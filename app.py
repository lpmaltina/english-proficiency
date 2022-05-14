from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.base import BaseEstimator, TransformerMixin
import pickle
import joblib
import json
import os
import spacy
import streamlit as st
from text import Text


class PassthroughTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        self.X = X
        return X

    def get_feature_names(self):
        return self.X.columns.tolist()


class MyTfidfVectorizer(TfidfVectorizer):
    def fit_transform(self, raw_documents, y=None):
        X = TfidfVectorizer.fit_transform(self, raw_documents, y=None)
        return X / X.sum(axis=1)

    def transform(self, raw_documents):
        X = TfidfVectorizer.transform(self, raw_documents)
        return X / X.sum(axis=1)


@st.cache(allow_output_mutation=True)
def load_models_and_data(
    abstract_nouns_file, concrete_nouns_file, word2level_file, pipeline_file
):
    try:
        nlp = spacy.load("en_core_web_lg")
    except IOError:
        spacy.cli.download("en_core_web_lg")
        nlp = spacy.load("en_core_web_lg")
    with open(abstract_nouns_file, "rb") as f:
        abstract = pickle.load(f)
    with open(concrete_nouns_file, "rb") as f:
        concrete = pickle.load(f)
    with open(word2level_file, "r") as f:
        word2level = json.load(f)
    pipeline = joblib.load(pipeline_file)
    return nlp, abstract, concrete, word2level, pipeline


nlp, abstract, concrete, word2level, pipeline = load_models_and_data(
    abstract_nouns_file=os.path.join("serialized", "abstract_nouns.pkl"),
    concrete_nouns_file=os.path.join("serialized", "concrete_nouns.pkl"),
    word2level_file=os.path.join("serialized", "word2level.json"),
    pipeline_file=os.path.join("serialized", "all-lr.joblib"),
)

st.title("Text Complexity for English")
text = st.text_area("Paste your text below", height=300)

if st.button("Get Level"):
    tokens = nlp(text)
    text_df = Text(tokens).create_df(abstract, concrete, word2level)
    st.text(f"{pipeline.predict(text_df)[0]}")
