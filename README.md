# Calm Capybara
## An approach for the SemEval 2018 Task 2: Multilingual Emoji Prediction
### [working title]

This project was conducted for the *Deep Learning for Natural Language Technologies* course of the Universiteit van Amsterdam's
Master Artificial Intelligence program during the winter term 2018/2019. 

### Task descritiption

[TODO: Task description goes here]

### Results

The results are split up for the english and the spanish part of the data set. All models' performances were determined 
on the test set. 

#### English 

|  Model|Precision |Recall  |F1-score  |
|------:|:----------|:-------|:---------|
|Bag-of-Words + Logistic Regression | 0.3281 | 0.2972 | 0.3018 |
|Bag-of-Words + SVM  | 0.2482 | 0.2520 | 0.2424 |

#### Spanish

| Model | Precision | Recall | F1-score |
|------:|:----------|:-------|:---------|


### Usage

[TODO. Explain how to use the whole thing]

1. Install the dependencies with

```sh
pip install -r requirements.txt
```

2. Read the datasets, process them and serialize the results:

```sh
python tweet_data.py
```

3. Read pretrained embeddings and serialize only those in the vocabulary:

```sh
python embeddings.py
```

4. Train a simple LSTM classifier:

```sh
python lstm.py
```

5. Monitor training with Tensorboard by running (in the same directory)

```sh
tensorboard --logdir=runs
```

and going to [http://localhost:6006](http://localhost:6006)
