`timescale 1ns/1ps

module tb_oqpsk;

    logic clk;
    logic rst_n;
    logic [15:0] data_in;
    logic data_valid;
    logic busy;
    logic signed [15:0] i_out;
    logic signed [15:0] q_out;

    // Ornekleme saati 10 ns, bir sembol 4 ornek = 40 ns.
    // Q gecikmesi SPS/2 = 2 ornek = 20 ns.
    oqpsk_modulator #(
        .SPS (4)
    ) dut (
        .clk     (clk),
        .rst_n   (rst_n),
        .data_in (data_in),
        .data_valid (data_valid),
        .busy     (busy),
        .i_out   (i_out),
        .q_out   (q_out)
    );

    initial clk = 1'b0;
    always #5 clk = ~clk;

    initial begin
        $dumpfile("oqpsk.vcd");
        $dumpvars(0, tb_oqpsk);

        rst_n     = 1'b0;
        data_in   = 16'd0;
        data_valid = 1'b0;

        // Reset iki saat kenari boyunca etkin.
        repeat (2) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;

        // MSB'den LSB'ye sembol ciftleri: 10,01,10,01,10,01,10,01.
        // I ve Q her sembolde terslenerek gorunur gecis olusturur.
        data_in    = 16'b1001_1001_1001_1001;
        data_valid = 1'b1;
        @(negedge clk);
        data_valid = 1'b0;

        // Buffer'in sekiz OQPSK sembolunu tamamlamasini bekle.
        @(negedge busy);
        @(negedge clk);
        #1;
        $display("Simulasyon tamamlandi. Dalga dosyasi: oqpsk.vcd");
        $finish;
    end

    // Tasarim kurali: bir ornekleme saatinde I ve Q birlikte degismemeli.
    logic signed [15:0] previous_i;
    logic signed [15:0] previous_q;

    always @(negedge clk) begin
        if (!rst_n) begin
            previous_i = i_out;
            previous_q = q_out;
        end else begin
            if ((i_out != previous_i) && (q_out != previous_q)) begin
                $error("I ve Q ayni bit suresinde birlikte degisti: t=%0t", $time);
                $fatal;
            end
            previous_i = i_out;
            previous_q = q_out;
        end
    end

endmodule
