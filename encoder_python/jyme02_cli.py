import argparse
import sys

import config as cfg
from jyme02 import JYME02


def build_parser():
    parser = argparse.ArgumentParser(
        prog="Witmotion JY-ME02-485 angular encoder",
        description="Configure and read values from a JY-ME02-485 absolute encoder over RS-485",
    )

    parser.add_argument("--port", "--com", dest="port", default=cfg.PORT,
                        help=f"Serial port, e.g. COM9 or /dev/ttyUSB0 (default {cfg.PORT})")

    parser.add_argument("--device-id", type=lambda x: int(x, 0),
                        default=cfg.DEFAULT_DEVICE_ID,
                        help=f"Modbus device/slave ID (default: 0x50). "
                             f"Accepts hex (0x..) or decimal (default {cfg.DEFAULT_DEVICE_ID})")

    parser.add_argument("--baud", type=int, default=cfg.DEFAULT_BAUD,
                        help=f"Serial baudrate (default: {cfg.DEFAULT_BAUD})")

    parser.add_argument("--timeout", type=float, default=cfg.DEFAULT_TIMEOUT_SEC,
                        help=f"Serial read timeout in seconds (default: {cfg.DEFAULT_TIMEOUT_SEC})")

    parser.add_argument("--averages", type=int, default=cfg.DEFAULT_AVERAGES,
                        help=f"Number of reads to average for read commands "
                             f"(default: {cfg.DEFAULT_AVERAGES})")

    subparsers = parser.add_subparsers(dest="action", required=True)

    # read
    read_commands = (cmd for cmd in cfg.COMMANDS if cfg.COMMANDS[cmd].get("read", False))
    read_parser = subparsers.add_parser("read", help="Read one or more register values")
    read_parser.add_argument("command", nargs="+", choices=sorted(read_commands),
                             help="One or more registers to read, e.g. 'angle rot temp'")

    # write
    write_commands = (cmd for cmd in cfg.COMMANDS if cfg.COMMANDS[cmd].get("write", False))
    write_parser = subparsers.add_parser("write", help="Write a value to a register")
    write_parser.add_argument("command", choices=sorted(write_commands),
                              help="Which register to write")
    write_parser.add_argument("value", help="Value to write (number or string option, "
                                            "e.g. 90, cw, multi)")
    write_parser.add_argument("--no-wrap", action="store_true",
                              help="Skip automatic unlock/save wrapping around the write")

    # general-purpose, no extra args
    for name, help_text in [
        ("unlock", "Unlock config registers for writing"),
        ("save", "Save current settings to non-volatile memory"),
        ("reset", "Reset settings to factory defaults"),
        ("restart", "Power-cycle / restart the device"),
        ("benchmark", "Read every known register and print the results"),
    ]:
        subparsers.add_parser(name, help=help_text)

    return parser


def coerce_value(raw):
    """Try to interpret a CLI string as int/float; fall back to the raw string
    so things like 'cw', 'multi', 'single' pass through to encoders unchanged"""
    try:
        return int(raw, 0)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def main():
    parser = build_parser()
    args = parser.parse_args()

    device = JYME02(
        device_id=args.device_id,
        com=args.port,
        baud=args.baud,
        timeout=args.timeout,
        averages=args.averages,
    )

    try:
        if args.action == "read":
            for command in args.command:
                result = device.read(command)
                print(f"{command}: {result}")

        elif args.action == "write":
            value = coerce_value(args.value)
            # TODO: investigate need of this flag
            if args.no_wrap:
                device.write(args.command, value)
            else:
                device.write_wrapped(args.command, value)
            print(f"{args.command} <- {value} (ok)")

        elif args.action == "unlock":
            # TODO: same here
            device.unlock()
            print("unlocked")

        elif args.action == "save":
            # TODO: same
            device.save()
            print("saved")

        elif args.action == "reset":
            device.reset()
            print("reset to factory defaults")

        elif args.action == "restart":
            device.restart()
            print("restart command sent")

        elif args.action == "benchmark":
            device.benchmark_read()

    except (ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # TODO: move to main project dir and update README
    main()
