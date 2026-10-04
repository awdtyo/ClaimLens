"""Iteration 1: train method X on dataset D (toy fixture code)."""

import csv

EPOCHS = 10
LEARNING_RATE = 0.01


def load_split(path):
    with open(path, encoding="utf-8") as handle:
        return list(csv.reader(handle))


def train(rows):
    weights = [0.0] * 4
    for _ in range(EPOCHS):
        for row in rows:
            features = [float(value) for value in row[:-1]]
            label = int(row[-1])
            score = sum(weight * feature for weight, feature in zip(weights, features))
            prediction = 1 if score > 0 else 0
            for index in range(len(weights)):
                weights[index] += LEARNING_RATE * (label - prediction) * features[index]
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
    print(f"accuracy={accuracy(model, test_rows):.4f}")
