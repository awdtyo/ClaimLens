# Method Z Reaches 85.0% Accuracy on Dataset Q

## 1. Introduction

We study classification on the made-up dataset Q. Baseline W is a small
network trained with default settings. Method Z adds one extra layer.
Method Z reaches 85.0% accuracy on dataset Q, versus 81.5% for baseline
W (see Table 1).

## 2. Method

Both models are trained for 5 epochs with a fixed seed of 1 and a
learning rate of 0.02. Batch size is 32.

## 3. Results

Table 1 reports test accuracy on dataset Q. Method Z reaches 85.0%
accuracy, a gain of 3.5 percentage points over baseline W at 81.5%.

Table 1: Test accuracy on dataset Q.

| Method | Accuracy (%) |
|--------|--------------|
| Z | 85.0 |
| W (baseline) | 81.5 |
