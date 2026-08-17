/*
 * ADALM-Pluto RX capture utility for libiio 0.x.
 *
 * Captures the two signed 12-bit RX scan channels and writes normalized
 * little-endian float32 I,Q pairs (complex64), directly compatible with the
 * standalone CPFSK demodulator in ../c_demod/cpfsk_demod.c.
 */

#define _CRT_SECURE_NO_WARNINGS
#include <errno.h>
#include <iio.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { float i, q; } complex32_t;

typedef struct {
    const char *uri;
    const char *output;
    const char *gain_mode;
    long long frequency_hz;
    long long sample_rate_hz;
    long long bandwidth_hz;
    double manual_gain_db;
    size_t samples;
    size_t buffer_samples;
} options_t;

static void usage(const char *exe) {
    fprintf(stderr,
        "Usage: %s --output FILE [options]\n"
        "  --uri URI             default: usb:\n"
        "  --frequency HZ        default: 2400000000\n"
        "  --sample-rate HZ      default: 30720000\n"
        "  --bandwidth HZ        default: 18000000\n"
        "  --samples COUNT       default: 262144\n"
        "  --buffer COUNT        default: 32768\n"
        "  --gain-mode MODE      slow_attack, fast_attack, hybrid or manual\n"
        "  --gain DB             manual gain; default: 30\n",
        exe);
}

static int parse_ll(const char *s, long long *value) {
    char *end = NULL;
    errno = 0;
    long long v = strtoll(s, &end, 10);
    if (errno || !end || *end || v <= 0) return 0;
    *value = v;
    return 1;
}

static int parse_size(const char *s, size_t *value) {
    long long v;
    if (!parse_ll(s, &v)) return 0;
    *value = (size_t)v;
    return (long long)*value == v;
}

static int parse_double(const char *s, double *value) {
    char *end = NULL;
    errno = 0;
    double v = strtod(s, &end);
    if (errno || !end || *end || !isfinite(v)) return 0;
    *value = v;
    return 1;
}

static int parse_args(int argc, char **argv, options_t *o) {
    int i;
    memset(o, 0, sizeof(*o));
    o->uri = "usb:";
    o->gain_mode = "slow_attack";
    o->frequency_hz = 2400000000LL;
    o->sample_rate_hz = 30720000LL;
    o->bandwidth_hz = 18000000LL;
    o->manual_gain_db = 30.0;
    o->samples = 262144;
    o->buffer_samples = 32768;

    for (i = 1; i < argc; ++i) {
        const char *a = argv[i];
        if (!strcmp(a, "--help") || !strcmp(a, "-h")) return -1;
        if (i + 1 >= argc) return 0;
        const char *v = argv[++i];
        if (!strcmp(a, "--uri")) o->uri = v;
        else if (!strcmp(a, "--output")) o->output = v;
        else if (!strcmp(a, "--gain-mode")) o->gain_mode = v;
        else if (!strcmp(a, "--frequency")) { if (!parse_ll(v, &o->frequency_hz)) return 0; }
        else if (!strcmp(a, "--sample-rate")) { if (!parse_ll(v, &o->sample_rate_hz)) return 0; }
        else if (!strcmp(a, "--bandwidth")) { if (!parse_ll(v, &o->bandwidth_hz)) return 0; }
        else if (!strcmp(a, "--samples")) { if (!parse_size(v, &o->samples)) return 0; }
        else if (!strcmp(a, "--buffer")) { if (!parse_size(v, &o->buffer_samples)) return 0; }
        else if (!strcmp(a, "--gain")) { if (!parse_double(v, &o->manual_gain_db)) return 0; }
        else return 0;
    }
    return o->output != NULL;
}

static void print_iio_error(const char *what, int error) {
    char text[256];
    iio_strerror(error < 0 ? -error : error, text, sizeof(text));
    fprintf(stderr, "%s: %s (%d)\n", what, text, error);
}

static int write_ll(const struct iio_channel *ch, const char *attr, long long value) {
    int r = iio_channel_attr_write_longlong(ch, attr, value);
    if (r < 0) print_iio_error(attr, r);
    return r >= 0;
}

static int write_text(const struct iio_channel *ch, const char *attr, const char *value) {
    ssize_t r = iio_channel_attr_write(ch, attr, value);
    if (r < 0) print_iio_error(attr, (int)r);
    return r >= 0;
}

int main(int argc, char **argv) {
    options_t o;
    int parsed = parse_args(argc, argv, &o);
    struct iio_context *ctx = NULL;
    struct iio_device *phy = NULL, *rxdev = NULL;
    struct iio_channel *rx_cfg = NULL, *rx_lo = NULL, *rx_i = NULL, *rx_q = NULL;
    struct iio_buffer *buffer = NULL;
    FILE *fp = NULL;
    complex32_t *converted = NULL;
    size_t written = 0;
    double sum_i = 0.0, sum_q = 0.0, sum_power = 0.0, peak = 0.0;
    int exit_code = 1;

    if (parsed <= 0) {
        usage(argv[0]);
        return parsed < 0 ? 0 : 2;
    }

    ctx = iio_create_context_from_uri(o.uri);
    if (!ctx) {
        fprintf(stderr, "Cannot create IIO context '%s': %s\n", o.uri, strerror(errno));
        goto cleanup;
    }
    iio_context_set_timeout(ctx, 5000);

    phy = iio_context_find_device(ctx, "ad9361-phy");
    rxdev = iio_context_find_device(ctx, "cf-ad9361-lpc");
    if (!phy || !rxdev) {
        fprintf(stderr, "Pluto RX devices were not found.\n");
        goto cleanup;
    }
    rx_cfg = iio_device_find_channel(phy, "voltage0", false);
    rx_lo = iio_device_find_channel(phy, "altvoltage0", true);
    rx_i = iio_device_find_channel(rxdev, "voltage0", false);
    rx_q = iio_device_find_channel(rxdev, "voltage1", false);
    if (!rx_cfg || !rx_lo || !rx_i || !rx_q) {
        fprintf(stderr, "Required Pluto RX channels were not found.\n");
        goto cleanup;
    }

    if (!write_ll(rx_lo, "frequency", o.frequency_hz) ||
        !write_ll(rx_cfg, "sampling_frequency", o.sample_rate_hz) ||
        !write_ll(rx_cfg, "rf_bandwidth", o.bandwidth_hz) ||
        !write_text(rx_cfg, "gain_control_mode", o.gain_mode)) {
        fprintf(stderr, "Pluto RX configuration failed.\n");
        goto cleanup;
    }
    if (!strcmp(o.gain_mode, "manual")) {
        char gain[64];
        snprintf(gain, sizeof(gain), "%.3f", o.manual_gain_db);
        if (!write_text(rx_cfg, "hardwaregain", gain)) goto cleanup;
    }

    iio_channel_enable(rx_i);
    iio_channel_enable(rx_q);
    buffer = iio_device_create_buffer(rxdev, o.buffer_samples, false);
    if (!buffer) {
        fprintf(stderr, "Cannot create RX buffer: %s\n", strerror(errno));
        goto cleanup;
    }
    converted = (complex32_t *)malloc(o.buffer_samples * sizeof(*converted));
    if (!converted) {
        fprintf(stderr, "Out of memory.\n");
        goto cleanup;
    }
    fp = fopen(o.output, "wb");
    if (!fp) {
        fprintf(stderr, "Cannot open output '%s': %s\n", o.output, strerror(errno));
        goto cleanup;
    }

    while (written < o.samples) {
        ssize_t bytes = iio_buffer_refill(buffer);
        char *pi, *pq, *end;
        ptrdiff_t step;
        size_t count = 0, wanted;
        if (bytes < 0) {
            print_iio_error("RX buffer refill", (int)bytes);
            goto cleanup;
        }
        pi = (char *)iio_buffer_first(buffer, rx_i);
        pq = (char *)iio_buffer_first(buffer, rx_q);
        end = (char *)iio_buffer_end(buffer);
        step = iio_buffer_step(buffer);
        wanted = o.samples - written;
        for (; pi < end && pq < end && count < wanted; pi += step, pq += step) {
            int16_t raw_i = 0, raw_q = 0;
            double power, magnitude;
            iio_channel_convert(rx_i, &raw_i, pi);
            iio_channel_convert(rx_q, &raw_q, pq);
            converted[count].i = (float)raw_i / 2048.0f;
            converted[count].q = (float)raw_q / 2048.0f;
            sum_i += converted[count].i;
            sum_q += converted[count].q;
            power = (double)converted[count].i * converted[count].i +
                    (double)converted[count].q * converted[count].q;
            sum_power += power;
            magnitude = sqrt(power);
            if (magnitude > peak) peak = magnitude;
            ++count;
        }
        if (!count || fwrite(converted, sizeof(*converted), count, fp) != count) {
            fprintf(stderr, "Output write failed.\n");
            goto cleanup;
        }
        written += count;
    }

    printf("Pluto RX capture complete\n");
    printf("uri=%s frequency=%lld Hz sample_rate=%lld Hz bandwidth=%lld Hz\n",
           o.uri, o.frequency_hz, o.sample_rate_hz, o.bandwidth_hz);
    printf("gain_mode=%s samples=%zu duration=%.6f s\n",
           o.gain_mode, written, (double)written / o.sample_rate_hz);
    printf("mean_i=%.9f mean_q=%.9f rms=%.9f peak=%.9f\n",
           sum_i / written, sum_q / written, sqrt(sum_power / written), peak);
    printf("complex64_output=%s bytes=%zu\n", o.output, written * sizeof(complex32_t));
    exit_code = 0;

cleanup:
    if (fp) fclose(fp);
    free(converted);
    if (buffer) iio_buffer_destroy(buffer);
    if (rx_i) iio_channel_disable(rx_i);
    if (rx_q) iio_channel_disable(rx_q);
    if (ctx) iio_context_destroy(ctx);
    return exit_code;
}
