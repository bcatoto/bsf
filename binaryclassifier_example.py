# https://medium.com/machine-learning-intuition/document-classification-part-2-text-processing-eaa26d16c719
# https://stackabuse.com/overview-of-classification-methods-in-python-with-scikit-learn/
# TODO Idea: for each abstract that we scrape, first check if it's relevant before adding it to MongoDB

# import statements
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# the initial data: convert into tf-idf vectors
arr = ["Car was cleaned by Jack",
	"Jack was cleaned by Car."]

# make a vector
vectorizer = TfidfVectorizer() # You can still specify n-grams and other parameters here.
X = vectorizer.fit_transform(arr)

print(X.toarray())

# train model
logreg_clf = LogisticRegression()

# not certain about the code below
Y = [0, 1] # This is the list where we could keep track of relevant/not relevant info (double check)
logreg_clf.fit(X, Y)
predictions = logreg_clf.predict(X)

score = logreg_clf.score(X, Y)
print(score)