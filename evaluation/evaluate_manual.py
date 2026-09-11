import json

INPUT_PATH = "evaluation/manual_evaluation.json"


def load_evaluation(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def calculate_metrics(evaluations):
    criteria = [
        "location_accuracy",
        "topic_relevance",
        "boundary_quality",
        "coverage",
        "redundancy",
    ]

    metrics = {}

    for criterion in criteria:
        passed = sum(
            1
            for evaluation in evaluations
            if evaluation[criterion] == "Pass"
        )

        total = len(evaluations)
        percentage = (passed / total) * 100 if total else 0

        metrics[criterion] = {
            "passed": passed,
            "total": total,
            "percentage": round(percentage, 2),
        }

    overall_passed = sum(
        1
        for evaluation in evaluations
        if evaluation["overall"] == "Pass"
    )

    metrics["overall"] = {
        "passed": overall_passed,
        "total": len(evaluations),
        "percentage": round(
            (overall_passed / len(evaluations)) * 100, 2
        ) if evaluations else 0,
    }

    return metrics


def main():
    data = load_evaluation(INPUT_PATH)
    evaluations = data["evaluations"]

    metrics = calculate_metrics(evaluations)

    print("=== DepoIndex Manual Topic Evaluation ===")
    print()
    print(f"Topics evaluated: {len(evaluations)}")
    print()

    print("Evaluation Metrics:")
    print()

    for criterion, result in metrics.items():
        if criterion == "overall":
            continue

        print(
            f"{criterion}: "
            f"{result['passed']}/{result['total']} "
            f"({result['percentage']}%)"
        )

    print()
    print(
        f"Overall: "
        f"{metrics['overall']['passed']}/"
        f"{metrics['overall']['total']} "
        f"({metrics['overall']['percentage']}%)"
    )


if __name__ == "__main__":
    main()