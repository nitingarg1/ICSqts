from experiment.assumption_package import assumption_banner


def main() -> None:
    print(assumption_banner())
    print("Validator scaffold only. L2 validation decisions are not populated in assumption package.")


if __name__ == "__main__":
    main()
