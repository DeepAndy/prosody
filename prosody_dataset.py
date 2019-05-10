import os
from torch.utils import data
from pytorch_pretrained_bert import BertTokenizer
from sklearn.model_selection import train_test_split
import torch
import numpy as np
import nltk

DATADIR = "data/"


class Dataset(data.Dataset):
    def __init__(self, tagged_sents, tag_to_index):
        sents, tags_li = [], [] # list of lists
        for sent in tagged_sents:
            words = [word_tag[0] for word_tag in sent]
            tags = [word_tag[1] for word_tag in sent]
            sents.append(["[CLS]"] + words + ["[SEP]"])
            tags_li.append(["<pad>"] + tags + ["<pad>"])
        self.sents, self.tags_li = sents, tags_li
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased', do_lower_case=True)
        self.tag_to_index = tag_to_index

    def __len__(self):
        return len(self.sents)

    def __getitem__(self, id):
        words, tags = self.sents[id], self.tags_li[id] # words, tags: string list

        x, y = [], [] # list of ids
        is_main_piece = [] # only score the main piece of each word
        for w, t in zip(words, tags):
            tokens = self.tokenizer.tokenize(w) if w not in ("[CLS]", "[SEP]") else [w]
            xx = self.tokenizer.convert_tokens_to_ids(tokens)

            t = [t] + ["<pad>"] * (len(tokens) - 1)  # <PAD>: no decision
            yy = [self.tag_to_index[each] for each in t]  # (T,)

            head = [1] + [0]*(len(tokens) - 1) # identify the main piece of each word

            x.extend(xx)
            is_main_piece.extend(head)
            y.extend(yy)

        assert len(x) == len(y) == len(is_main_piece), "len(x)={}, len(y)={}, len(is_main_piece)={}".format(len(x), len(y), len(is_main_piece))
        # seqlen
        seqlen = len(y)

        # to string
        words = " ".join(words)
        tags = " ".join(tags)
        return words, x, is_main_piece, tags, y, seqlen


def load_dataset(config):
    directory = os.fsencode(DATADIR)
    tagged_sents = []
    vocab = []
    files = 0
    for file in os.listdir(directory):
        files += 1
        filename = os.fsdecode(file)
        if filename.endswith(".txt"):
            with open(DATADIR+filename) as f:
                lines = f.read().splitlines()
                sent = []
                for line in lines:
                    split_line = line.split('\t')
                    sent.append((split_line[0], split_line[1]))
                    vocab.append(split_line[0])
            tagged_sents.append(sent)
        else:
            break
        if files >= config.number_of_sents:
            break

    vocab = set(vocab)
    vocab_size = len(vocab)
    tags = list(set(word_tag[1] for sent in tagged_sents for word_tag in sent))
    tags = ["<pad>"] + tags

    tag_to_index = {tag: index for index, tag in enumerate(tags)}
    index_to_tag = {index: tag for index, tag in enumerate(tags)}

    # Split the data into train, dev and test
    train_data, validation_data = train_test_split(tagged_sents, test_size=2*config.test_and_dev_split)
    dev_data, test_data = train_test_split(validation_data, test_size=.5)

    print('Training data: {}'.format(len(train_data)))
    print('Dev data: {}'.format(len(dev_data)))
    print('Test data: {}'.format(len(test_data)))

    return train_data, test_data, dev_data, tag_to_index, index_to_tag, vocab_size


def pad(batch):
    # Pad sentences to the longest sample
    f = lambda x: [sample[x] for sample in batch]
    words = f(0)
    is_main_piece = f(2)
    tags = f(3)
    seqlens = f(-1)
    maxlen = np.array(seqlens).max()

    f = lambda x, seqlen: [sample[x] + [0] * (seqlen - len(sample[x])) for sample in batch] # 0: <pad>
    x = f(1, maxlen)
    y = f(-2, maxlen)

    f = torch.LongTensor

    return words, f(x), is_main_piece, tags, f(y), seqlens
