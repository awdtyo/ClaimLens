# Method X Improves Classification Accuracy on Dataset D

This is a made-up toy paper used as a fixture for ClaimLens development
and tests. All numbers below are invented.

## 1. Introduction

We study image classification on the made-up dataset D. The baseline
method Y is a small convolutional network trained with default settings.
We propose method X, which adds a normalization step before the final
layer. Our main finding is that method X reaches 91.2% accuracy on
dataset D, versus 88.0% for baseline Y (see Table 1).

## 2. Method

Method X extends baseline Y with one extra normalization layer. Both
models are trained for 10 epochs with a fixed seed of 0 and a learning
rate of 0.01. Batch size is 64.

## 3. Experiments

We split the made-up dataset D into 800 training and 200 test examples.
Each model is trained once on the training split and evaluated once on
the test split. Accuracy is the fraction of correct test predictions.

## 4. Results

Table 1 reports test accuracy on dataset D. Method X reaches 91.2%
accuracy, a gain of 3.2 percentage points over baseline Y at 88.0%.

Table 1: Test accuracy on dataset D.

| Method       | Accuracy (%) |
|--------------|--------------|
| X            | 91.2         |
| Y (baseline) | 88.0         |
