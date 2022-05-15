import math
import pandas as pd
from wordfreq import zipf_frequency


LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


class Text:
    def __init__(self, tokens):
        self.tokens = tokens
        self.lemmas = self.lemmatize()
        if len(self.lemmas) < 5:
            raise ValueError("The text must have at least 5 words")
        self.dependencies = self.get_dependencies()

    def lemmatize(self):
        return [token.lemma_.lower() for token in self.tokens if token.is_alpha]

    def count_words(self):
        n_words = 0
        for token in self.tokens:
            if token.is_alpha:
                n_words += 1
        return n_words

    def count_sentences(self):
        n_sentences = 0
        for _ in self.tokens.sents:
            n_sentences += 1
        return n_sentences

    def count_type_token_ratio(self):
        return len(set(self.lemmas)) / len(self.lemmas)

    def count_words_from_wordlist(self, wordlist):
        words_from_wordlists = 0

        for lemma in self.lemmas:
            if lemma in wordlist:
                words_from_wordlists += 1

        return words_from_wordlists / len(self.lemmas)

    def count_words_from_level_lists(self, word2level):
        level_freqs = {level: 0 for level in LEVELS}

        for lemma in self.lemmas:
            level = word2level.get(lemma)
            if level:
                level_freqs[level] += 1

        for level in level_freqs:
            level_freqs[level] /= len(self.lemmas)

        return level_freqs

    def count_zipf_freqs(self):
        zipf_freqs = {}

        for lemma in self.lemmas:
            zipf_freq = math.floor(zipf_frequency(lemma, "en"))
            if zipf_freq in zipf_freqs:
                zipf_freqs[zipf_freq] += 1
            else:
                zipf_freqs[zipf_freq] = 1

        for zipf_freq in zipf_freqs:
            zipf_freqs[zipf_freq] /= len(self.lemmas)

        return zipf_freqs

    def get_pos(self):
        return " ".join([token.pos_ for token in self.tokens if token.is_alpha])

    def get_dependencies(self):
        return " ".join([token.dep_ for token in self.tokens if token.is_alpha])

    def count_mean_noun_chunk_len(self):
        noun_chunks = list(self.tokens.noun_chunks)
        len_noun_chunks = [len(noun_chunk) for noun_chunk in noun_chunks]
        if len_noun_chunks:
            sum(len_noun_chunks) / len(noun_chunks)
        return 0

    def count_passiveness(self):
        active = 0
        passive = 0

        for dep in self.dependencies:
            if dep in {"aux", "csubj", "nsubj"}:
                active += 1
            elif dep in {"aux_pass", "csubjpass", "nsubjpass"}:
                passive += 1

        passiveness = 0

        if passive + active > 0:
            passiveness = passive / (active + passive)

        return passiveness

    def count_mean_num_dependencies(self):
        num_dependencies = 0
        for token in self.tokens:
            if token.is_alpha:
                for child in token.children:
                    if child.is_alpha:
                        num_dependencies += 1
        if self.dependencies:
            return num_dependencies / len(self.dependencies)
        return 0

    def count_mean_arc_len(self):
        sum_arc_len = 0
        n_arcs = 0
        for token in self.tokens:
            if token.is_alpha:
                for child in token.children:
                    if child.is_alpha:
                        sum_arc_len += abs(token.i - child.i) - 1
                        n_arcs += 1
        if n_arcs:
            return sum_arc_len / n_arcs
        return 0

    def create_df(self, abstract_nouns, concrete_nouns, word2level):
        dct = {
            "words": [" ".join(self.lemmas)],
            "word_count": [self.count_words()],
            "type_token_ratio": [self.count_type_token_ratio()],
            "abstract_nouns": [self.count_words_from_wordlist(abstract_nouns)],
            "concrete_nouns": [self.count_words_from_wordlist(concrete_nouns)],
            "pos": [self.get_pos()],
            "dep": [self.get_dependencies()],
            "mean_noun_chunk_len": [self.count_mean_noun_chunk_len()],
            "passiveness": [self.count_passiveness()],
            "mean_num_dependencies": [self.count_mean_num_dependencies()],
            "mean_arc_len": [self.count_mean_arc_len()],
        }

        zipf_freqs = self.count_zipf_freqs()

        for i in range(1, 7):
            dct[f"zipf_freqs_{i}"] = zipf_freqs.get(i, 0)

        levels = self.count_words_from_level_lists(word2level)
        for level in LEVELS:
            dct[level] = [levels[level]]

        df = pd.DataFrame(dct)
        return df
