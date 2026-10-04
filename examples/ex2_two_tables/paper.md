# Method V Trains Fast on Dataset R

## 1. Introduction

We study classification on the made-up dataset R. Method V is a small
network with early stopping. Method V reaches 90.0% accuracy on dataset
R (see Table 1) and trains in 12 minutes on one GPU (see Table 2).

## 2. Method

The model is trained for 4 epochs with a fixed seed of 2 and a learning
rate of 0.05. Batch size is 16.

## 3. Results

Table 1 reports test accuracy on dataset R. Table 2 reports training
time in minutes on one GPU.

Table 1: Accuracy on dataset R.

| Method | Accuracy (%) |
|--------|--------------|
| V | 90.0 |

Table 2: Training time.

| Method | Minutes |
|--------|---------|
| V | 12 |
