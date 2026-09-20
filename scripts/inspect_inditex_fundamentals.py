from collections import defaultdict

from src.providers.yahoo_fundamentals import (
    YahooFundamentalsProvider,
)


def main() -> None:
    provider = YahooFundamentalsProvider()

    records = provider.get_annual_financials(
        company_id=1,
        symbol="ITX.MC",
    )

    grouped = defaultdict(list)

    for record in records:
        grouped[record.statement_type.value].append(record)

    print()
    print("INDITEX FUNDAMENTALS INSPECTION")
    print("=" * 80)
    print(f"Provider: {provider.name}")
    print(f"Total normalized records: {len(records)}")
    print()

    for statement_type, statement_records in grouped.items():
        print(statement_type.upper())
        print("-" * 80)

        statement_records.sort(
            key=lambda record: (
                record.metric.value,
                record.period_end,
            )
        )

        for record in statement_records:
            print(
                f"{record.period_end} | "
                f"{record.metric.value:<25} | "
                f"{record.value:>18,.4f} | "
                f"publication_date="
                f"{record.publication_date}"
            )

        print()


if __name__ == "__main__":
    main()