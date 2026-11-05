# Firmware hooks

A hook is a small C function that runs *instead of* a firmware function. Use
one when the real function needs hardware the emulator does not have, or when
it is the place where input should enter the firmware.

You write a hook once. The fuzzer (triforce-qemu) and the concolic executor
(concolic-executor) both run that same code.

## 1. A story: waiting for a key

The STM32 example firmware blinks an LED and waits for a key on its UART:

```c
uint8_t key;                                  /* lives on the stack, at sp + 0xb */
for (;;) {
    HAL_GPIO_TogglePin(LED);                  /* reads the GPIO output register */
    HAL_Delay(1);
    while (HAL_UART_Receive(&huart, &key, 1, 100) != HAL_OK)
        ;
    if (key == 's')
        start();                              /* 0x0800043a: the branch we want */
    else
        uart_printf("%c != s\n", key);
}
```

There is no real UART in the emulator. We hook `HAL_UART_Receive` so the key
comes straight from the input file:

```c
/* hooks.c */
FIRMWARE_HOOK(uart_recv)
{
    hook_input_to_guest(cs, hook_arg(cs, 1), (uint16_t)hook_arg(cs, 2)); /* buffer, length */
    hook_set_ret(cs, 0);                                                  /* HAL_OK */
}
```

```json
"patch": [{"symbol": "HAL_UART_Receive", "hook": "uart_recv"}]
```

That is all. The hook does not say "make this symbolic", does not know which
engine runs it, and does not return to the caller by itself.

## 2. The input file is a tape

Think of the input file as a tape. Every reader cuts the next bytes off the
front: an MMIO read of 4 bytes takes 4, and `uart_recv` takes 1. For the STM32
example, measured with a 4 KiB input:

```text
offset:  0 ............ 1663 | 1664 | 1665..1668 | 1669 | 1670..1673 | 1674 | ...
reader:  startup: clock, GPIO| key  | LED toggle | key  | LED toggle | key  |
         (MMIO, 4 bytes each)|      | (MMIO)     |      |            |      |
```

Both engines cut the tape in exactly the same way, so **byte 1664 is the first
key in both engines**. The concolic executor gives that byte a name:
`input[1664]`. The whole design rests on this rule:

> Symbolic byte *k* always means byte *k* of the input file.

Here is what happens to the first key:

| Step | Fuzzer | Concolic executor |
| --- | --- | --- |
| `uart_recv` takes byte 1664 (`0xff`) | `key = 0xff` | `key = 0xff`, known as `input[1664]` |
| `if (key == 's')` | not taken | not taken; the solver is asked: "when is `input[1664] == 's'`?" |
| Solver answer | | a new input file, the same as before but with byte 1664 = `0x73` |
| The fuzzer runs that new file | `key = 's'`, the branch is taken | |

We ran exactly this on `alexis`, and the new input reached `0x0800043a`.

### What went wrong before

The old configuration had no receive hook. It used `symbolize_at_pc`, which
made the stack byte `key` symbolic when the firmware loaded it. But that
feature counted on its own, starting at zero. So it called the key `input[0]`,
even though the real key came from byte 1664 or later.

The solver did its job: "make `input[0]` be `'s'`". It wrote the 1-byte file
`s`. The fuzzer then gave that `'s'` to the **first clock register read** during
startup, and the key was untouched. In the same test, none of the 9 inputs it
generated reached the `'s'` branch. `symbolize_at_pc` has been removed, and a
configuration that still uses it stops at startup.

## 3. Writing a hook

```c
FIRMWARE_HOOK(get_packet)          /* int get_packet(uint8_t *buf): always 16 bytes */
{
    hook_input_to_guest(cs, hook_arg(cs, 0), 16);
    hook_set_ret(cs, 16);
}
```

`FIRMWARE_HOOK(name)` defines the hook and registers it under `name`, the
name your configuration uses. There is no table to edit. Add the hook to
`hooks/hooks.c` in the shared `hooks` submodule.

| Call | What it does |
| --- | --- |
| `hook_arg(cs, n)` | The n-th argument of the hooked function (0 is the first). |
| `hook_set_ret(cs, v)` | Its return value. |
| `hook_input_to_guest(cs, addr, len)` | Take the next `len` bytes of the tape and put them at `addr`. |
| `hook_read_mem(cs, addr, buf, len)` | Read guest memory, as a firmware load would. |
| `hook_write_mem(cs, addr, buf, len)` | Write fixed bytes into guest memory. |
| `hook_read_reg` / `hook_write_reg` | Read or write a register by number. |
| `hook_log(fmt, ...)` | Write to the engine's log (`-d afl_fuzzing_log` or `-d concolic_replay`). |

A few rules keep the two engines in step:

- **Take input only with `hook_input_to_guest`.** It moves the tape forward and,
  in the concolic executor, gives each byte its `input[k]` name.
- **Change guest state only through these calls.** They also drop old symbolic
  values. For example, after `hook_set_ret`, r0 is a plain number.
- **Write one version.** There is no `#ifdef` for the engine; the engine
  differences live below the API (section 5).
- **Don't return to the caller yourself.** After your hook, the runtime applies
  `ret` (if the patch entry has one) and jumps back to the caller (PC := LR).

When a hook writes into guest memory, the buffer must be RAM the firmware may
write. Anything else (flash, MMIO, a bad pointer) aborts the run, which both
engines report as a crash. For `hook_input_to_guest`, this happens before any
input is taken:

```text
qemu-system-arm: hook: guest 0x1f6 is not writable RAM
```

## 4. Pointing the configuration at a hook

A patch entry says where to intercept and which hook to run:

```json
{
  "symbols": "stm32h7s78-dk.syms",
  "patch": [
    {"addr": "0x08002648", "hook": "HAL_Delay"},
    {"symbol": "HAL_UART_Receive", "hook": "uart_recv"},
    {"symbol": "uart_printf", "hook": "stub", "ret": 0}
  ]
}
```

- `addr` or `symbol` (one of the two): where the function starts.
- `hook`: the hook name. The older spelling `name` still works.
- `ret`: optional; the value callers see. With `stub`, it skips a function and
  returns that value. The third entry above silences `uart_printf`.

Most firmware is stripped, so addresses come from your disassembler.
`symbols` lets you name them once and use the names everywhere. Write a small
file next to the configuration, one `address [type] name` per line. That is
what `nm` prints, so `arm-none-eabi-nm fw.elf > fw.syms` works whenever an
unstripped build exists:

```text
# names I gave functions in Ghidra
08004d50 T HAL_UART_Receive
0x08002648 HAL_Delay
```

Thumb addresses may be odd (`0x08004d51`); bit 0 is cleared for you.

Mistakes stop both engines at startup, before any input is used:

```text
qemu-system-arm: patch[1]: unknown hook "printf"; registered hooks: HAL_Delay, stub, uart_printf, uart_recv
qemu-system-arm: patch[2]: symbol "HAL_UART_Receive" has more than one address
qemu-system-arm: ./fw.syms:2: expected "address [type] name"
```

A name listed twice with different addresses is only an error when a patch
uses it. [Writing a firmware configuration](firmware-configuration.md) has the
full field reference.

## 5. Under the hood

The code is split so that only five small calls differ between the engines:

| Layer | File | Written | Job |
| --- | --- | --- | --- |
| Hooks | `hooks/hooks.c` | once | What the firmware function should do. |
| API | `hooks/hook_api.h` | once | The calls in section 3. |
| Core | `hooks/core.c` | once | Configuration, dispatch, copies into guest memory. |
| ABI | `hooks/arm/abi.c` | once per architecture | Where arguments, return value and return address live. |
| Port | `hw/<engine>/hook_port.c` | once per engine | Input tape and symbolic bookkeeping. |

Everything in `hooks/` is one repository, checked out as the `hooks` submodule
of both QEMU forks. Here is the path of one `uart_recv` call:

```text
firmware: bl HAL_UART_Receive -> a new translation block starts at 0x08004d50
  translate.c   arm_helper_func(cpu, pc)            both engines; pc is passed in
  core.c        hook_dispatch: 0x08004d50 -> uart_recv
  hooks.c         uart_recv(cs)
  abi.c             hook_arg(cs, 1) = r1, hook_arg(cs, 2) = r2
  core.c            hook_input_to_guest(cs, buf, 1)
  port                hook_port_take_input: offset = cursor; getFuzz(...)
  core.c              copy into guest RAM, one page at a time
  port                hook_port_mem_input(host, 1, offset)
                        fuzzer: nothing    concolic: host byte = input[offset]
  abi.c             hook_set_ret(cs, 0): r0 = 0, r0 has no symbolic value now
  abi.c         hook_arch_return: pc = lr & ~1
translate.c     returns 1, and the block jumps to the new pc
```

The port, per engine:

| Port call | Fuzzer | Concolic executor |
| --- | --- | --- |
| `hook_port_take_input` | `getFuzz`, return the old cursor | the same |
| `hook_port_mem_input` | nothing | `_sym_make_symbolic(host, len, offset)` |
| `hook_port_mem_concrete` | nothing | clear the bytes' symbolic values |
| `hook_port_reg_concrete` | nothing | clear the register's symbolic value |
| `hook_port_log` | `LOG_AFL` | `LOG_CONCOLIC_REPLAY` |

MMIO reads follow the same rule: the concolic executor names them
`input[cursor]`, `input[cursor + 1]`, …, so hook input and MMIO input mix
freely on one tape.

**Why copy page by page?** Two guest pages next to each other need not be next
to each other in host memory. Say a buffer starts 4 bytes before a page
boundary. Its first 4 bytes are on one host page, and the rest may be anywhere
else. The core copies each page part through its own host pointer, and the
symbolic names follow the same split: `input[k..k+3]`, then `input[k+4..]`.

**Why pass `pc` into the helper?** It is the exact address of the block being
entered. `regs[15]` is only up to date when blocks are not chained. Both
engines turn chaining off today, so this does not change behaviour now. It
keeps hooks working if chaining is ever turned on.

## 6. Changing a hook

1. Edit `hooks.c` in the `firmware-hooks` repository; commit and push.
2. Point the `hooks` submodule of **both** QEMU forks at that commit.
3. Record both QEMU commits here, in `concolic-fuzzing`.

`build_fuzzer_and_concolic_executor.sh` refuses to build if the two forks pin
different hook commits.

To check a change, run the same firmware and input in both engines and compare
the traces, as `tests/check_coverage_export.py` does. Also replay a concolic
test case in the fuzzer, and check that it reaches the branch it was solved for.

## 7. Limits

- Input goes into guest memory, not straight into a register. A hook that must
  return an input value can put it in memory, or the firmware can read it there.
- Arguments are used at their current values. If `len` was symbolic, the solver
  does not learn that the hook depended on it.
- When the tape runs out inside a hook, the run ends, exactly as for an MMIO read.
- Hooks run at translation-block starts. Patch function entries, where `lr`
  holds the return address.
