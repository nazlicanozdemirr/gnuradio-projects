/*
 * Standalone complex64 CPFSK/CPM demodulator.
 * No GNU Radio or external DSP library is required.
 */

#define _CRT_SECURE_NO_WARNINGS
#include <errno.h>
#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

typedef struct { float i, q; } complex32_t;

typedef enum { MODE_FULL, MODE_PARTIAL } demod_mode_t;

typedef struct {
    const char *name;
    double fs;
    double rs;
    double center_hz;
    double deviation_hz;
    demod_mode_t mode;
} profile_t;

static const profile_t PROFILES[] = {
    {"A", 576000.0, 9600.0, -872.0454545454545, 3515.4545454545455, MODE_FULL},
    {"B", 576000.0, 9600.0,  108.08155457653852, 2228.043151619129, MODE_PARTIAL},
    {"C", 576000.0, 9600.0, -123.63636363636364, 2947.5, MODE_FULL},
};

typedef struct {
    const char *input_path;
    const char *output_prefix;
    const char *profile_name;
    double fs;
    double rs;
    double center_hz;
    double deviation_hz;
    demod_mode_t mode;
    int mode_set;
    int timing_set;
    double timing_offset;
    int invert;
} options_t;

typedef struct {
    double c0, c1;
    double rms;
    double quality;
    double one_fraction;
    double threshold;
} cluster2_t;

typedef struct {
    uint8_t *bits;
    float *soft;
    size_t count;
    double timing_offset;
    size_t timing_updates;
    double timing_error_rms;
    double final_sps;
    cluster2_t cluster;
} symbols_t;

typedef struct {
    size_t flags;
    size_t candidate_frames;
    size_t byte_aligned_frames;
    size_t crc_ok_frames;
} hdlc_stats_t;

static void usage(const char *exe) {
    fprintf(stderr,
        "Usage: %s --input FILE --output PREFIX --profile A|B|C [options]\n"
        "Options:\n"
        "  --fs HZ             sample rate (default/profile value)\n"
        "  --rs BAUD           symbol rate\n"
        "  --center HZ         discriminator frequency center\n"
        "  --deviation HZ      effective peak frequency deviation\n"
        "  --mode full|partial full-response integrate or pulse-shaped sampling\n"
        "  --timing SAMPLES    force fractional symbol-boundary offset\n"
        "  --invert            invert sliced line symbols\n"
        "  --help              show this help\n\n"
        "Profiles use measurements from intern_Rec(), intern_Rec1(), intern_Rec2().\n",
        exe);
}

static const profile_t *find_profile(const char *name) {
    size_t i;
    for (i = 0; i < sizeof(PROFILES)/sizeof(PROFILES[0]); ++i)
        if (_stricmp(PROFILES[i].name, name) == 0) return &PROFILES[i];
    return NULL;
}

static int parse_double(const char *s, double *out) {
    char *end = NULL;
    errno = 0;
    double v = strtod(s, &end);
    if (errno || !end || *end != '\0' || !isfinite(v)) return 0;
    *out = v;
    return 1;
}

static int parse_args(int argc, char **argv, options_t *o) {
    int i;
    memset(o, 0, sizeof(*o));
    o->fs = 576000.0;
    o->rs = 9600.0;
    o->mode = MODE_FULL;
    for (i = 1; i < argc; ++i) {
        const char *a = argv[i];
        if (!strcmp(a, "--help") || !strcmp(a, "-h")) return -1;
        if (!strcmp(a, "--invert")) { o->invert = 1; continue; }
        if (i + 1 >= argc) { fprintf(stderr, "Missing value after %s\n", a); return 0; }
        const char *v = argv[++i];
        if (!strcmp(a, "--input")) o->input_path = v;
        else if (!strcmp(a, "--output")) o->output_prefix = v;
        else if (!strcmp(a, "--profile")) o->profile_name = v;
        else if (!strcmp(a, "--fs")) { if (!parse_double(v, &o->fs)) return 0; }
        else if (!strcmp(a, "--rs")) { if (!parse_double(v, &o->rs)) return 0; }
        else if (!strcmp(a, "--center")) { if (!parse_double(v, &o->center_hz)) return 0; }
        else if (!strcmp(a, "--deviation")) { if (!parse_double(v, &o->deviation_hz)) return 0; }
        else if (!strcmp(a, "--timing")) {
            if (!parse_double(v, &o->timing_offset)) return 0;
            o->timing_set = 1;
        } else if (!strcmp(a, "--mode")) {
            if (!strcmp(v, "full")) o->mode = MODE_FULL;
            else if (!strcmp(v, "partial")) o->mode = MODE_PARTIAL;
            else { fprintf(stderr, "Unknown mode: %s\n", v); return 0; }
            o->mode_set = 1;
        } else { fprintf(stderr, "Unknown option: %s\n", a); return 0; }
    }

    if (o->profile_name) {
        const profile_t *p = find_profile(o->profile_name);
        if (!p) { fprintf(stderr, "Unknown profile: %s\n", o->profile_name); return 0; }
        /* Apply profile first, then re-read explicit numeric overrides. */
        double fs_arg = o->fs, rs_arg = o->rs, center_arg = o->center_hz, dev_arg = o->deviation_hz;
        int fs_explicit = 0, rs_explicit = 0, center_explicit = 0, dev_explicit = 0;
        for (i = 1; i < argc; ++i) {
            if (!strcmp(argv[i], "--fs")) fs_explicit = 1;
            else if (!strcmp(argv[i], "--rs")) rs_explicit = 1;
            else if (!strcmp(argv[i], "--center")) center_explicit = 1;
            else if (!strcmp(argv[i], "--deviation")) dev_explicit = 1;
        }
        o->fs = fs_explicit ? fs_arg : p->fs;
        o->rs = rs_explicit ? rs_arg : p->rs;
        o->center_hz = center_explicit ? center_arg : p->center_hz;
        o->deviation_hz = dev_explicit ? dev_arg : p->deviation_hz;
        if (!o->mode_set) o->mode = p->mode;
    }
    if (!o->input_path || !o->output_prefix) {
        fprintf(stderr, "--input and --output are required.\n"); return 0;
    }
    if (!(o->fs > 0.0) || !(o->rs > 0.0) || !(o->deviation_hz > 0.0)) {
        fprintf(stderr, "fs, rs and deviation must be positive.\n"); return 0;
    }
    return 1;
}

static int make_name(char *dst, size_t n, const char *prefix, const char *suffix) {
    int r = snprintf(dst, n, "%s%s", prefix, suffix);
    return r >= 0 && (size_t)r < n;
}

static complex32_t *read_iq(const char *path, size_t *count, double *mean_mag,
                            double *rms_mag, double *peak_mag,
                            double *mean_i, double *mean_q) {
    FILE *fp = fopen(path, "rb");
    long bytes;
    complex32_t *x;
    size_t got, i;
    double sm = 0.0, sp = 0.0, si = 0.0, sq = 0.0, peak = 0.0;
    if (!fp) { fprintf(stderr, "Cannot open input %s: %s\n", path, strerror(errno)); return NULL; }
    if (fseek(fp, 0, SEEK_END) || (bytes = ftell(fp)) < 0 || fseek(fp, 0, SEEK_SET)) {
        fprintf(stderr, "Cannot determine input length.\n"); fclose(fp); return NULL;
    }
    if (bytes % (long)sizeof(complex32_t)) {
        fprintf(stderr, "Input size is not divisible by 8; not raw complex64.\n"); fclose(fp); return NULL;
    }
    *count = (size_t)bytes / sizeof(complex32_t);
    x = (complex32_t *)malloc(*count * sizeof(*x));
    if (!x) { fprintf(stderr, "Out of memory reading IQ.\n"); fclose(fp); return NULL; }
    got = fread(x, sizeof(*x), *count, fp);
    fclose(fp);
    if (got != *count) { fprintf(stderr, "Short IQ read.\n"); free(x); return NULL; }
    for (i = 0; i < *count; ++i) {
        double ii = x[i].i, qq = x[i].q;
        double p = ii*ii + qq*qq, m = sqrt(p);
        if (!isfinite(ii) || !isfinite(qq)) {
            fprintf(stderr, "Non-finite IQ sample at %zu.\n", i); free(x); return NULL;
        }
        si += ii; sq += qq; sm += m; sp += p; if (m > peak) peak = m;
    }
    *mean_mag = sm / *count;
    *rms_mag = sqrt(sp / *count);
    *peak_mag = peak;
    *mean_i = si / *count;
    *mean_q = sq / *count;
    return x;
}

static float *quadrature_discriminator(const complex32_t *x, size_t n, double fs) {
    size_t i;
    float *f;
    const double scale = fs / (2.0 * M_PI);
    if (n < 2) return NULL;
    f = (float *)malloc((n-1) * sizeof(*f));
    if (!f) return NULL;
    for (i = 1; i < n; ++i) {
        double dot = (double)x[i].i*x[i-1].i + (double)x[i].q*x[i-1].q;
        double cross = (double)x[i].q*x[i-1].i - (double)x[i].i*x[i-1].q;
        f[i-1] = (float)(atan2(cross, dot) * scale);
    }
    return f;
}

static float *centered_moving_average(const float *x, size_t n, int length) {
    size_t i;
    int half = length/2;
    double sum = 0.0;
    float *y = (float *)malloc(n*sizeof(*y));
    if (!y) return NULL;
    size_t initial_hi = (size_t)half < n ? (size_t)half : n-1;
    for (i = 0; i <= initial_hi; ++i) sum += x[i];
    for (i = 0; i < n; ++i) {
        if (i > 0) {
            size_t add = i + (size_t)half;
            if (add < n) sum += x[add];
            if (i > (size_t)half) sum -= x[i-(size_t)half-1];
        }
        size_t lo = i > (size_t)half ? i-(size_t)half : 0;
        size_t hi_candidate = i + (size_t)half;
        size_t hi = hi_candidate < n ? hi_candidate : n-1;
        y[i] = (float)(sum / (double)(hi-lo+1));
    }
    return y;
}

static double *prefix_sum(const float *x, size_t n) {
    size_t i;
    double *p = (double *)malloc((n+1)*sizeof(*p));
    if (!p) return NULL;
    p[0] = 0.0;
    for (i = 0; i < n; ++i) p[i+1] = p[i] + x[i];
    return p;
}

static double integral_at(const double *prefix, const float *x, size_t n, double t) {
    if (t <= 0.0) return 0.0;
    if (t >= (double)n) return prefix[n];
    size_t k = (size_t)floor(t);
    return prefix[k] + (t-(double)k)*x[k];
}

static double interp_float(const float *x, size_t n, double t) {
    if (t <= 0.0) return x[0];
    if (t >= (double)(n-1)) return x[n-1];
    size_t k = (size_t)floor(t);
    double a = t-(double)k;
    return (1.0-a)*x[k] + a*x[k+1];
}

static int compare_double(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

static cluster2_t cluster2(const double *v, size_t n) {
    size_t i, it;
    cluster2_t r;
    double *copy = NULL;
    double c0, c1, threshold;
    memset(&r, 0, sizeof(r));
    if (n < 2) return r;
    copy = (double *)malloc(n*sizeof(*copy));
    if (!copy) return r;
    memcpy(copy, v, n*sizeof(*copy));
    qsort(copy, n, sizeof(*copy), compare_double);
    c0 = copy[n/5]; c1 = copy[(4*n)/5];
    free(copy);
    for (it = 0; it < 20; ++it) {
        double s0 = 0.0, s1 = 0.0; size_t n0 = 0, n1 = 0;
        threshold = 0.5*(c0+c1);
        for (i = 0; i < n; ++i) {
            if (v[i] <= threshold) { s0 += v[i]; ++n0; }
            else { s1 += v[i]; ++n1; }
        }
        if (!n0 || !n1) break;
        double nc0 = s0/n0, nc1 = s1/n1;
        if (fabs(nc0-c0)+fabs(nc1-c1) < 1e-9) { c0=nc0; c1=nc1; break; }
        c0=nc0; c1=nc1;
    }
    threshold = 0.5*(c0+c1);
    double sse = 0.0; size_t ones = 0;
    for (i = 0; i < n; ++i) {
        double d;
        if (v[i] > threshold) { d=v[i]-c1; ++ones; } else d=v[i]-c0;
        sse += d*d;
    }
    r.c0=c0; r.c1=c1; r.threshold=threshold;
    r.rms=sqrt(sse/n); r.quality=(c1-c0)/(2.0*r.rms+DBL_MIN);
    r.one_fraction=(double)ones/n;
    return r;
}

static size_t timing_values(const float *freq, const float *smooth, const double *prefix,
                            size_t n, double sps, double offset, demod_mode_t mode,
                            double start, double stop, double *out, size_t cap) {
    size_t count = 0;
    double first = offset + ceil((start-offset)/sps)*sps;
    double t;
    for (t = first; t+sps < stop && count < cap; t += sps) {
        if (mode == MODE_FULL)
            out[count++] = (integral_at(prefix,freq,n,t+sps)-integral_at(prefix,freq,n,t))/sps;
        else
            out[count++] = interp_float(smooth,n,t+0.5*sps);
    }
    return count;
}

static double recover_timing(const float *freq, const float *smooth, const double *prefix,
                             size_t n, double fs, double sps, demod_mode_t mode,
                             cluster2_t *best_cluster) {
    double start = fmin((double)n*0.05, fs);
    double stop = fmin((double)n, start + 5.0*fs);
    size_t cap = (size_t)((stop-start)/sps)+4;
    double *values = (double *)malloc(cap*sizeof(*values));
    double best_q = -1.0, best_offset = 0.0;
    cluster2_t best = {0};
    int steps = (int)ceil(2.0*sps); /* half-sample timing grid */
    int p;
    if (!values) return 0.0;
    for (p = 0; p < steps; ++p) {
        double offset = (double)p*sps/steps;
        size_t count = timing_values(freq,smooth,prefix,n,sps,offset,mode,start,stop,values,cap);
        cluster2_t c = cluster2(values,count);
        if (c.quality > best_q) { best_q=c.quality; best_offset=offset; best=c; }
    }
    free(values);
    *best_cluster=best;
    return best_offset;
}

static symbols_t extract_symbols(const float *freq, const float *smooth, const double *prefix,
                                 size_t n, const options_t *o, double timing) {
    symbols_t s;
    double sps = o->fs/o->rs;
    double first = timing + ceil((0.0-timing)/sps)*sps;
    size_t cap = (size_t)(((double)n-first)/sps)+2;
    size_t k = 0;
    double t;
    memset(&s,0,sizeof(s));
    s.bits=(uint8_t *)malloc(cap);
    s.soft=(float *)malloc(cap*sizeof(float));
    if (!s.bits || !s.soft) { free(s.bits); free(s.soft); memset(&s,0,sizeof(s)); return s; }
    for (t=first; t+sps<(double)n; t+=sps) {
        double hz;
        if (o->mode == MODE_FULL)
            hz=(integral_at(prefix,freq,n,t+sps)-integral_at(prefix,freq,n,t))/sps;
        else
            hz=interp_float(smooth,n,t+0.5*sps);
        s.soft[k]=(float)((hz-o->center_hz)/o->deviation_hz);
        s.bits[k]=(uint8_t)((hz>o->center_hz) ? 1 : 0);
        if (o->invert) s.bits[k]^=1;
        ++k;
    }
    s.count=k; s.timing_offset=timing; s.final_sps=sps;
    if (k) {
        double *hz=(double *)malloc(k*sizeof(*hz));
        if (hz) {
            size_t i; for(i=0;i<k;++i) hz[i]=(double)s.soft[i]*o->deviation_hz+o->center_hz;
            s.cluster=cluster2(hz,k); free(hz);
        }
    }
    return s;
}

/*
 * Transition-aided timing tracker for pulse-shaped/partial-response CPFSK.
 *
 * The initial timing search supplies a nominal symbol boundary.  Whenever two
 * adjacent hard symbols differ, a true symbol transition must exist near the
 * predicted boundary.  The nearest threshold crossing is therefore a direct
 * timing observation.  A small proportional/frequency loop follows slow clock
 * drift without relying on a GNU Radio timing-recovery block.
 */
static symbols_t extract_symbols_tracking(const float *smooth, size_t n,
                                           const options_t *o, double timing) {
    const double nominal_sps=o->fs/o->rs;
    const double alpha=0.25;
    const double beta=0.005;
    const double search_fraction=0.38;
    const double min_sps=nominal_sps*0.995;
    const double max_sps=nominal_sps*1.005;
    double omega=nominal_sps, t=timing, err_sq=0.0;
    size_t cap=(size_t)((double)n/min_sps)+4, k=0, updates=0;
    symbols_t s;
    memset(&s,0,sizeof(s));
    s.bits=(uint8_t*)malloc(cap);
    s.soft=(float*)malloc(cap*sizeof(float));
    if(!s.bits||!s.soft){free(s.bits);free(s.soft);memset(&s,0,sizeof(s));return s;}

    if(t+0.5*omega<(double)n-1.0){
        double hz=interp_float(smooth,n,t+0.5*omega);
        s.soft[k]=(float)((hz-o->center_hz)/o->deviation_hz);
        s.bits[k]=(uint8_t)(hz>o->center_hz);
        if(o->invert)s.bits[k]^=1;
        ++k;
    }

    while(k<cap && t+1.6*omega<(double)n){
        double predicted=t+omega;
        double hz=interp_float(smooth,n,predicted+0.5*omega);
        uint8_t current=(uint8_t)(hz>o->center_hz);
        uint8_t previous=(uint8_t)(s.bits[k-1]^(o->invert?1:0));

        if(current!=previous){
            long lo=(long)floor(predicted-search_fraction*omega);
            long hi=(long)ceil(predicted+search_fraction*omega);
            double best_distance=DBL_MAX,best_crossing=predicted;
            long j;
            if(lo<1)lo=1;
            if(hi>(long)n-2)hi=(long)n-2;
            for(j=lo;j<=hi;++j){
                double a=(double)smooth[j]-o->center_hz;
                double b=(double)smooth[j+1]-o->center_hz;
                if((a<=0.0&&b>0.0)||(a>=0.0&&b<0.0)){
                    double crossing=(double)j-a/(b-a);
                    double distance=fabs(crossing-predicted);
                    if(distance<best_distance){best_distance=distance;best_crossing=crossing;}
                }
            }
            if(best_distance<search_fraction*omega){
                double error=best_crossing-predicted;
                predicted+=alpha*error;
                omega+=beta*error;
                if(omega<min_sps)omega=min_sps;
                if(omega>max_sps)omega=max_sps;
                err_sq+=error*error;
                ++updates;
                hz=interp_float(smooth,n,predicted+0.5*omega);
                current=(uint8_t)(hz>o->center_hz);
            }
        }

        s.soft[k]=(float)((hz-o->center_hz)/o->deviation_hz);
        s.bits[k]=(uint8_t)(current^(o->invert?1:0));
        ++k;
        t=predicted;
    }

    s.count=k;
    s.timing_offset=timing;
    s.timing_updates=updates;
    s.timing_error_rms=updates?sqrt(err_sq/updates):0.0;
    s.final_sps=omega;
    if(k){
        double *hz_values=(double*)malloc(k*sizeof(*hz_values));
        if(hz_values){
            size_t i;
            for(i=0;i<k;++i)hz_values[i]=(double)s.soft[i]*o->deviation_hz+o->center_hz;
            s.cluster=cluster2(hz_values,k);
            free(hz_values);
        }
    }
    return s;
}

static uint8_t *nrzi_decode(const uint8_t *line, size_t n, int one_is_no_transition, size_t *out_n) {
    size_t i;
    uint8_t *out;
    if (n < 2) return NULL;
    out=(uint8_t *)malloc(n-1);
    if (!out) return NULL;
    for(i=1;i<n;++i) {
        uint8_t no_transition=(uint8_t)(line[i]==line[i-1]);
        out[i-1]=one_is_no_transition ? no_transition : (uint8_t)!no_transition;
    }
    *out_n=n-1; return out;
}

static uint8_t *g3ruh_descramble(const uint8_t *in, size_t n) {
    size_t i; uint32_t state=0; uint8_t *out=(uint8_t *)malloc(n);
    if(!out) return NULL;
    for(i=0;i<n;++i) {
        uint8_t r=in[i]&1u;
        out[i]=(uint8_t)(r ^ ((state>>11)&1u) ^ ((state>>16)&1u));
        state=((state<<1)|r)&0x1ffffu;
    }
    return out;
}

static int write_raw(const char *path, const void *data, size_t item_size, size_t count) {
    FILE *fp=fopen(path,"wb");
    if(!fp){fprintf(stderr,"Cannot write %s\n",path);return 0;}
    if(fwrite(data,item_size,count,fp)!=count){fclose(fp);return 0;}
    fclose(fp);return 1;
}

static uint8_t *pack_bits(const uint8_t *bits, size_t n, int msb_first, size_t bit_offset, size_t *bytes_n) {
    size_t i,j;
    if(bit_offset>=n){*bytes_n=0;return NULL;}
    *bytes_n=(n-bit_offset)/8;
    uint8_t *out=(uint8_t *)calloc(*bytes_n,1);
    if(!out)return NULL;
    for(i=0;i<*bytes_n;++i)for(j=0;j<8;++j){
        uint8_t b=bits[bit_offset+8*i+j]&1u;
        if(msb_first)out[i]|=(uint8_t)(b<<(7-j)); else out[i]|=(uint8_t)(b<<j);
    }
    return out;
}

static int write_hex(const char *path, const uint8_t *data, size_t n) {
    size_t i,j; FILE *fp=fopen(path,"w"); if(!fp)return 0;
    for(i=0;i<n;i+=16){
        fprintf(fp,"%08zx  ",i);
        for(j=0;j<16;++j){if(i+j<n)fprintf(fp,"%02X ",data[i+j]);else fputs("   ",fp);}
        fputs(" ",fp);
        for(j=0;j<16&&i+j<n;++j){uint8_t c=data[i+j];fputc(c>=32&&c<127?c:'.',fp);}
        fputc('\n',fp);
    }
    fclose(fp);return 1;
}

static char *json_escape_copy(const char *src) {
    size_t i, n = 0;
    char *out, *p;
    for (i = 0; src[i]; ++i) n += (src[i]=='\\' || src[i]=='\"') ? 2 : 1;
    out = (char *)malloc(n+1);
    if (!out) return NULL;
    p = out;
    for (i = 0; src[i]; ++i) {
        if (src[i]=='\\' || src[i]=='\"') *p++='\\';
        *p++=src[i];
    }
    *p='\0';
    return out;
}

static size_t count_byte_value(const uint8_t *data, size_t n, uint8_t value) {
    size_t i, count=0;
    for(i=0;i<n;++i) count += data[i]==value;
    return count;
}

static uint16_t crc16_x25(const uint8_t *data,size_t n){
    size_t i;int j;uint16_t crc=0xffffu;
    for(i=0;i<n;++i){crc^=data[i];for(j=0;j<8;++j)crc=(crc&1u)?(uint16_t)((crc>>1)^0x8408u):(uint16_t)(crc>>1);}
    return (uint16_t)(crc^0xffffu);
}

static int is_flag_at(const uint8_t *b,size_t p){
    static const uint8_t flag[8]={0,1,1,1,1,1,1,0};
    size_t j;for(j=0;j<8;++j)if((b[p+j]&1u)!=flag[j])return 0;return 1;
}

static hdlc_stats_t analyze_hdlc(const uint8_t *bits,size_t n,FILE *frames){
    hdlc_stats_t st={0}; size_t *flags=NULL,fc=0,cap=0,i,j;
    for(i=0;i+8<=n;++i)if(is_flag_at(bits,i)){
        if(fc==cap){cap=cap?cap*2:64;size_t *q=(size_t*)realloc(flags,cap*sizeof(*q));if(!q)break;flags=q;}
        flags[fc++]=i;
    }
    st.flags=fc;
    for(i=0;i+1<fc;++i){
        size_t a=flags[i]+8,b=flags[i+1];
        if(b<=a||b-a<16)continue;
        ++st.candidate_frames;
        uint8_t *dst=(uint8_t*)malloc(b-a);size_t dn=0;int ones=0,bad=0;
        if(!dst)continue;
        for(j=a;j<b;++j){uint8_t bit=bits[j]&1u;if(bit){dst[dn++]=1;if(++ones>6){bad=1;break;}}
            else{if(ones==5){ones=0;continue;}dst[dn++]=0;ones=0;}}
        if(!bad&&dn>=16&&dn%8==0){
            size_t bytes_n=0;uint8_t *bytes=pack_bits(dst,dn,0,0,&bytes_n);++st.byte_aligned_frames;
            if(bytes&&bytes_n>=2){uint16_t want=(uint16_t)(bytes[bytes_n-2]|((uint16_t)bytes[bytes_n-1]<<8));uint16_t got=crc16_x25(bytes,bytes_n-2);
                int ok=(want==got);if(ok)++st.crc_ok_frames;
                if(frames)fprintf(frames,"frame=%zu bits=%zu bytes=%zu crc=%s expected=%04X calculated=%04X\n",i,dn,bytes_n,ok?"OK":"BAD",want,got);
            }free(bytes);
        }
        free(dst);
    }
    free(flags);return st;
}

static void bit_stats(const uint8_t *b,size_t n,double *ones,double *trans,size_t *max_run){
    size_t i,oc=0,run=0,mr=0;if(!n){*ones=*trans=0;*max_run=0;return;}
    for(i=0;i<n;++i){oc+=b[i]&1u;if(i==0||b[i]==b[i-1])++run;else{if(run>mr)mr=run;run=1;}}
    if(run>mr)mr=run;
    size_t tc=0;
    for(i=1;i<n;++i)tc+=(b[i]!=b[i-1]);
    *ones=(double)oc/n;*trans=n>1?(double)tc/(n-1):0;*max_run=mr;
}

int main(int argc,char **argv){
    options_t o;int pa=parse_args(argc,argv,&o);if(pa<=0){usage(argv[0]);return pa<0?0:2;}
    size_t iq_n=0,nf=0,i;double mean_mag,rms_mag,peak_mag,mean_i,mean_q;
    complex32_t *iq=read_iq(o.input_path,&iq_n,&mean_mag,&rms_mag,&peak_mag,&mean_i,&mean_q);
    if(!iq)return 3;
    float *freq=quadrature_discriminator(iq,iq_n,o.fs);free(iq);if(!freq){fprintf(stderr,"Discriminator allocation failed.\n");return 3;}nf=iq_n-1;
    float *smooth=centered_moving_average(freq,nf,21);if(!smooth){free(freq);return 3;}
    double *prefix=prefix_sum(freq,nf);if(!prefix){free(freq);free(smooth);return 3;}
    double sps=o.fs/o.rs;cluster2_t timing_cluster={0};
    double timing=o.timing_set?o.timing_offset:recover_timing(freq,smooth,prefix,nf,o.fs,sps,o.mode,&timing_cluster);
    symbols_t sym=(o.mode==MODE_PARTIAL)
        ? extract_symbols_tracking(smooth,nf,&o,timing)
        : extract_symbols(freq,smooth,prefix,nf,&o,timing);
    free(prefix);free(smooth);free(freq);
    if(!sym.bits||!sym.soft){fprintf(stderr,"Symbol extraction failed.\n");return 3;}

    size_t nrzi_n=0,alt_n=0;uint8_t *nrzi=nrzi_decode(sym.bits,sym.count,1,&nrzi_n);
    uint8_t *nrzi_alt=nrzi_decode(sym.bits,sym.count,0,&alt_n);
    uint8_t *descr=g3ruh_descramble(nrzi,nrzi_n);uint8_t *descr_alt=g3ruh_descramble(nrzi_alt,alt_n);
    if(!nrzi||!nrzi_alt||!descr||!descr_alt){fprintf(stderr,"Bit processing allocation failed.\n");return 3;}

    char name[4096];
#define WRITE_SUFFIX(suf,data,size,count) do{if(!make_name(name,sizeof(name),o.output_prefix,suf)||!write_raw(name,data,size,count)){fprintf(stderr,"Write failed: %s\n",suf);return 4;}}while(0)
    WRITE_SUFFIX(".soft_f32",sym.soft,sizeof(float),sym.count);
    WRITE_SUFFIX(".line_bits",sym.bits,1,sym.count);
    WRITE_SUFFIX(".nrzi_bits",nrzi,1,nrzi_n);
    WRITE_SUFFIX(".nrzi_alt_bits",nrzi_alt,1,alt_n);
    WRITE_SUFFIX(".g3ruh_bits",descr,1,nrzi_n);
    WRITE_SUFFIX(".g3ruh_alt_bits",descr_alt,1,alt_n);

    size_t msb_n=0,lsb_n=0;uint8_t *msb=pack_bits(descr,nrzi_n,1,0,&msb_n);uint8_t *lsb=pack_bits(descr,nrzi_n,0,0,&lsb_n);
    size_t best_bit_offset=0,best_flag_bytes=0,aligned_n=0;
    uint8_t *aligned=NULL;
    for(i=0;i<8;++i){
        size_t test_n=0;uint8_t *test=pack_bits(descr,nrzi_n,0,i,&test_n);
        size_t flags=count_byte_value(test,test_n,0x7e);
        if(i==0||flags>best_flag_bytes){free(aligned);aligned=test;aligned_n=test_n;best_flag_bytes=flags;best_bit_offset=i;}
        else free(test);
    }
    WRITE_SUFFIX(".bytes_msb.bin",msb,1,msb_n);
    WRITE_SUFFIX(".bytes_lsb_offset0.bin",lsb,1,lsb_n);
    WRITE_SUFFIX(".bytes_lsb.bin",aligned,1,aligned_n);
    make_name(name,sizeof(name),o.output_prefix,".hex.txt");write_hex(name,aligned,aligned_n);

    make_name(name,sizeof(name),o.output_prefix,".frames.txt");FILE *frames=fopen(name,"w");
    hdlc_stats_t h_line=analyze_hdlc(sym.bits,sym.count,NULL);
    hdlc_stats_t h_nrzi=analyze_hdlc(nrzi,nrzi_n,NULL);
    hdlc_stats_t h_descr=analyze_hdlc(descr,nrzi_n,frames);
    hdlc_stats_t h_descr_alt=analyze_hdlc(descr_alt,alt_n,NULL);
    if(frames)fclose(frames);

    double one_frac,trans_frac;size_t max_run;bit_stats(sym.bits,sym.count,&one_frac,&trans_frac,&max_run);
    double soft_mean=0,soft_sq=0,soft_abs=0;for(i=0;i<sym.count;++i){double z=sym.soft[i];soft_mean+=z;soft_sq+=z*z;soft_abs+=fabs(z);}soft_mean/=sym.count;soft_sq=sqrt(fmax(0,soft_sq/sym.count-soft_mean*soft_mean));soft_abs/=sym.count;

    make_name(name,sizeof(name),o.output_prefix,".report.json");FILE *report=fopen(name,"w");
    if(!report){fprintf(stderr,"Cannot write report.\n");return 4;}
    char *input_json=json_escape_copy(o.input_path);
    if(!input_json){fclose(report);return 4;}
    fprintf(report,
      "{\n"
      "  \"input\": \"%s\",\n  \"profile\": \"%s\",\n  \"mode\": \"%s\",\n"
      "  \"sample_rate_hz\": %.12g,\n  \"symbol_rate_baud\": %.12g,\n  \"samples_per_symbol\": %.12g,\n"
      "  \"center_hz\": %.12g,\n  \"deviation_hz\": %.12g,\n  \"modulation_index_h\": %.12g,\n"
      "  \"iq_samples\": %zu,\n  \"duration_seconds\": %.12g,\n"
      "  \"iq_mean_i\": %.12g,\n  \"iq_mean_q\": %.12g,\n  \"envelope_mean\": %.12g,\n  \"envelope_rms\": %.12g,\n  \"envelope_peak\": %.12g,\n  \"papr_db\": %.12g,\n"
      "  \"timing_offset_samples\": %.12g,\n  \"timing_search_quality\": %.12g,\n"
      "  \"timing_tracking_updates\": %zu,\n  \"timing_error_rms_samples\": %.12g,\n  \"final_samples_per_symbol\": %.12g,\n"
      "  \"symbols\": %zu,\n  \"symbol_one_fraction\": %.12g,\n  \"symbol_transition_fraction\": %.12g,\n  \"maximum_run_symbols\": %zu,\n"
      "  \"best_lsb_byte_bit_offset\": %zu,\n  \"aligned_0x7e_byte_count\": %zu,\n"
      "  \"soft_mean\": %.12g,\n  \"soft_std\": %.12g,\n  \"soft_mean_absolute\": %.12g,\n"
      "  \"observed_cluster_low_hz\": %.12g,\n  \"observed_cluster_high_hz\": %.12g,\n  \"observed_cluster_rms_hz\": %.12g,\n  \"observed_cluster_quality\": %.12g,\n"
      "  \"hdlc\": {\n"
      "    \"line\": {\"flags\": %zu, \"crc_ok\": %zu},\n"
      "    \"nrzi\": {\"flags\": %zu, \"crc_ok\": %zu},\n"
      "    \"nrzi_g3ruh\": {\"flags\": %zu, \"candidate_frames\": %zu, \"byte_aligned_frames\": %zu, \"crc_ok\": %zu},\n"
      "    \"nrzi_alt_g3ruh\": {\"flags\": %zu, \"crc_ok\": %zu}\n"
      "  }\n}\n",
      input_json,o.profile_name?o.profile_name:"custom",o.mode==MODE_FULL?"full":"partial",
      o.fs,o.rs,sps,o.center_hz,o.deviation_hz,2.0*o.deviation_hz/o.rs,
      iq_n,(double)iq_n/o.fs,mean_i,mean_q,mean_mag,rms_mag,peak_mag,20.0*log10(peak_mag/rms_mag),
      timing,timing_cluster.quality,sym.timing_updates,sym.timing_error_rms,sym.final_sps,
      sym.count,one_frac,trans_frac,max_run,best_bit_offset,best_flag_bytes,
      soft_mean,soft_sq,soft_abs,sym.cluster.c0,sym.cluster.c1,sym.cluster.rms,sym.cluster.quality,
      h_line.flags,h_line.crc_ok_frames,h_nrzi.flags,h_nrzi.crc_ok_frames,
      h_descr.flags,h_descr.candidate_frames,h_descr.byte_aligned_frames,h_descr.crc_ok_frames,
      h_descr_alt.flags,h_descr_alt.crc_ok_frames);
    fclose(report);free(input_json);

    printf("profile=%s mode=%s samples=%zu symbols=%zu sps=%.9f timing=%.6f\n",
           o.profile_name?o.profile_name:"custom",o.mode==MODE_FULL?"full":"partial",iq_n,sym.count,sps,timing);
    printf("center=%.3f Hz deviation=%.3f Hz h=%.6f one_fraction=%.6f transitions=%.6f\n",
           o.center_hz,o.deviation_hz,2.0*o.deviation_hz/o.rs,one_frac,trans_frac);
    printf("soft mean/std/abs=%.4f/%.4f/%.4f cluster quality=%.3f\n",soft_mean,soft_sq,soft_abs,sym.cluster.quality);
    if(sym.timing_updates)printf("timing tracker: updates=%zu error_rms=%.4f samples final_sps=%.9f\n",
                                 sym.timing_updates,sym.timing_error_rms,sym.final_sps);
    printf("HDLC flags: line=%zu nrzi=%zu g3ruh=%zu g3ruh_alt=%zu; aligned 0x7E bytes=%zu at bit offset=%zu; CRC OK=%zu\n",
           h_line.flags,h_nrzi.flags,h_descr.flags,h_descr_alt.flags,best_flag_bytes,best_bit_offset,h_descr.crc_ok_frames);
    printf("outputs=%s.*\n",o.output_prefix);

    free(sym.bits);free(sym.soft);free(nrzi);free(nrzi_alt);free(descr);free(descr_alt);free(msb);free(lsb);free(aligned);
    return 0;
}
