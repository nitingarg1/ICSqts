from experiment.assumption_package import assumption_banner


def main() -> None:
    print(assumption_banner())
    print("Freeze scaffold only. Use freeze/hashes.sha256 and freeze/EXPERIMENT_FREEZE.md for draft packaging.")


if __name__ == "__main__":
    main()
