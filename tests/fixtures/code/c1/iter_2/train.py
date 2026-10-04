"""Iteration 2: seeded rerun with logging (toy fixture code)."""

import csv
import random

EPOCHS = 10
LEARNING_RATE = 0.01
SEED = 0


def load_split(path):
    with open(path, encoding="utf-8") as handle:
        return list(csv.reader(handle))


def train(rows):
    random.seed(SEED)
    weights = [random.uniform(-0.01, 0.01) for _ in range(4)]
    for epoch in range(EPOCHS):
        for row in rows:
            features = [float(value) for value in row[:-1]]
            label = int(row[-1])
            score = sum(weight * feature for weight, feature in zip(weights, features))
            prediction = 1 if score > 0 else 0
            for index in range(len(weights)):
                weights[index] += LEARNING_RATE * (label - prediction) * features[index]
        print(f"epoch={epoch + 1} done")
    return weights


def accuracy(weights, rows):
    correct = 0
    for row in rows:
        features = [float(value) for value in row[:-1]]
        label = int(row[-1])
        score = sum(weight * feature for weight, feature in zip(weights, features))
        if (1 if score > 0 else 0) == label:
            correct += 1
    return correct / max(1, len(rows))


if __name__ == "__main__":
    train_rows = load_split("train.csv")
    test_rows = load_split("test.csv")
    model = train(train_rows)
    measured = accuracy(model, test_rows)
    print(f"accuracy={measured:.4f}")
    assert measured == 0.912, "must match the reported 91.2%"
