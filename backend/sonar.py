import pandas as pd
from hatesonar import Sonar

sonar = Sonar()

# Example usage:
ex = "At least I'm not a nigger"
info = sonar.ping(text=ex)


def extract_prediction(info):
    best = -float("inf")
    pred_class = None
    for i in range(len(info["classes"])):
        if info["classes"][i]["confidence"] > best:
            best = info["classes"][i]["confidence"]
            pred_class = info["classes"][i]["class_name"]
    return pred_class, best


pred_class, score = extract_prediction(info)
print("text:", ex)
print("class:", pred_class)
print("score:", score)


# Using our own collected dataset
data = pd.read_csv("labeled_data.csv")

for i in range(90, 110):
    tweet = data["tweet"][i]
    info = sonar.ping(text=tweet)
    pred_class, score = extract_prediction(info)
    print("text:", tweet)
    print("class:", pred_class)
    print("score:", score)
    print("___________")
