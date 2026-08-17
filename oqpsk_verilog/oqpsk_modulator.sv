`timescale 1ns/1ps

// 16 bit giris buffer'ini OQPSK I/Q taban-bant orneklerine donusturur.
// Bir sembol SPS saat ornegi surer; Q, I'den SPS/2 ornek gecikmelidir.
module oqpsk_modulator #(
    parameter integer SPS = 4
) (
    input  logic clk,
    input  logic rst_n,
    input  logic [15:0] data_in,
    input  logic data_valid,
    output logic busy,
    output logic signed [15:0] i_out,
    output logic signed [15:0] q_out
);

    // 16 bit isaretli tam olcek taban-bant seviyeleri.
    // Bit 1 -> +32767, bit 0 -> -32767
    localparam logic signed [15:0] POS_LEVEL =  16'sd32767;
    localparam logic signed [15:0] NEG_LEVEL = -16'sd32767;
    localparam integer HALF_SPS = SPS / 2;
    localparam integer SAMPLE_COUNT_WIDTH = (SPS <= 1) ? 1 : $clog2(SPS);

    logic [15:0] data_buffer;
    logic [2:0] symbol_index;
    logic [SAMPLE_COUNT_WIDTH-1:0] sample_count;

    initial begin
        if ((SPS < 2) || ((SPS % 2) != 0))
            $error("SPS en az 2 ve cift bir sayi olmalidir.");
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            data_buffer <= 16'sd0;
            symbol_index <= 3'd0;
            sample_count <= '0;
            busy          <= 1'b0;
            i_out         <= 16'sd0;
            q_out         <= 16'sd0;
        end else if (!busy) begin
            if (data_valid) begin
                // Yeni 16 bit kelimeyi dahili buffer'a al.
                data_buffer <= data_in;
                symbol_index <= 3'd0;
                sample_count <= '0;
                busy          <= 1'b1;
            end
        end else begin
            // Her sembolun MSB'den baslayarak I bitini ilk ornekte al.
            if (sample_count == 0)
                i_out <= data_buffer[15 - (symbol_index * 2)]
                       ? POS_LEVEL : NEG_LEVEL;

            // Q bitini yarim sembol (SPS/2 ornek) sonra al.
            if (sample_count == HALF_SPS)
                q_out <= data_buffer[14 - (symbol_index * 2)]
                       ? POS_LEVEL : NEG_LEVEL;

            if (sample_count == (SPS - 1)) begin
                sample_count <= '0;
                if (symbol_index == 3'd7) begin
                    busy <= 1'b0;
                end else begin
                    symbol_index <= symbol_index + 1'b1;
                end
            end else begin
                sample_count <= sample_count + 1'b1;
            end
        end
    end

endmodule
