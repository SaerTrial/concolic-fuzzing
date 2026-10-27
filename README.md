# Concolic Fuzzing
This repo sets up fuzzer and concolic executor for concolic fuzzing. Basically, it compiles TriforceQEMU and full system SymQEMU (concolic-replay). TriforceQEMU is another project that implements full system fuzzing with the help of rehosting. This setup only supports Linux machine. 

# Environment Setup
Install the following for QEMU compile.
```
sudo apt install git libglib2.0-dev libgcrypt20-dev     \
 zlib1g-dev autoconf                                    \
 automake libtool bison flex libpixman-1-dev            \
 python3-venv meson cmake python3-pip                   \
 llvm wget curl
```

Install Rust cargo
```
curl https://sh.rustup.rs -sSf | sh
```

Then run `./build_fuzzer_and_concolic_executor.sh` to build TriforceQEMU, concolic-replay, AFL++4.34.

# Run a test fuzzing

Run the fuzzer first.
``` 
mkdir ./AFLplusplus/input
mkdir ./AFLplusplus/output
perl -E 'say "A" x 80' > AFLplusplus/input/input1

./AFLplusplus/afl-fuzz                                   \
  -M fuzzer01                                            \
  -i ./AFLplusplus/input/                                \
  -o ./AFLplusplus/output                                \
  -t 2000                                                \
  --                                                     \
  ./TriforceQEMU/build/qemu-system-arm                   \
  -M rehost-fuzzing                                      \
  -display none                                          \
  -kernel ./fw-example/nucleo753zi/aflConfiguration.json \
  -aflFile @@
```

Run afl fuzzing helper that leverages concolic executor to guide fuzzing progress of main instance.
```
symcc_fuzzing_helper                                    \
 -v -o ./AFLplusplus/output                             \
 -a fuzzer01 -n symqemu                                 \
 -- ./concolic-replay/build/qemu-system-arm             \
 -M concolic-execution                                  \
 -display none                                          \
 -kernel ./TriforceQEMU/patches/fw-example/nucleo753zi/aflConfiguration.json                                                   \
  -replayFile @@
```


# Example

The image shows a fuzzer as a main instance running in parallel mode and scanning queue folders of other instances in the meanwhile.
![TriforceQEMU+AFL](./imgs/TriforceQEMU.png)


The symcc fuzzing helper watches new test cases of the main instance, and pick the most promising testcase for concolic exploration. It generates new testcase by following AFL testcase naming convention, which are taken advantage of when deemed interesting by the main instance fuzzer.
![Symcc fuzzing helper with full system concolic executor](./imgs/symcc_fuzzing_helper.png)



# Firmware Configuration

TriforceQEMU and concolic-replay both implement JSON configuration parsing in the same design, meaning that a same file can be shared in between.Consult `fw-example` to see any of configuration example. 

A configuration tells how QEMU sets up in terms of flash, ram, mmio, patched address, address to exit at, interrupt firing strategy, entrypoint, init cpu states, user hooks, etc.

## Symbolize memory access at a PC
Concolic-replay supports various symbolization strategies.Other than symbolizing mmio, another use case is to symbolize any memory access at a specified PC. This is helpful, I think, when an interesting taking input from outside stores the value in the stack. An trivial example is `var = uart_read(); if (var == 0)...`


```json
"aflPanicAddr": "0x08003d30",
"symbolize_at_pc": ["0x8004782", "0x8000ef0"], 
"entry_address": "0x8003de1",
```

## Write a user hook
Writing a user hook callback is kind of painful in this project since supporting a python layer like Unicorn is still a future work. See `hw/rehosting/arm/function_hooks.c` for TriforceQEMU or `hw/concolic/arm/function_hooks.c`, which has access to a cpu state instance and allows modification to cpu registers. 

## Interrupt firing strategy
Now, it only supports round-robin, and others like trigger a specific ISR at a PC, random pickup based on fuzzing values, etc, are still work in progress. Since this project aims at fuzzing exotic or ECU arch, implementing more interrupt firing strategies is not priority. Especially, this work becomes more complex when an interrupt controller is not available in QEMU and requires a build-up from scratch. Not really funny! 


# Colorizing code coverage in Ghidra Catographyer?
Append `-covFile cov.ezcov` to dump code coverage in order.

# Utility
* `utils/aggregate_queue_cov.sh`: make a cumulative code coverage;
* `utils/search_interesting_bb.sh`: look for interesting basic blocks, e.g., `search_interesting_bb.sh queue_folder bb1, bb2, bb3…` ;
* `test_same_exec_flows_over_testset.sh` and `utils/single_compare_test_case.sh`: compare whether execution flows between TriforceQEMU and concolic-replay are the same under a test case or a test set;



# Work in Progress

* Porting to RH850
* More coordination strategies between fuzzer and concolic executor
* More firmset under test (fuzzware, P2IM)
* Benchmarking pure AFL++ in hybrid mode and the one with concolic execution in use

