"""
Classes and methods to read, process, and serialize data from the Emoji Dataset
"""
import torch
from torch.utils import data
from torch.nn.utils.rnn import pad_sequence
import os
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import TfidfTransformer
import numpy as np
from scipy.sparse import lil_matrix
from sklearn.externals import joblib
from collections import OrderedDict

TEXT_EXT = '.text'
LABELS_EXT = '.labels'
UNK_SYMBOL = "<UNK>"
PAD_SYMBOL = "<PAD>"


class TweetsBaseDataset(data.Dataset):
    """ A Dataset class for the emoji prediction task. The base class reads
    the file to prepare a vocabulary that is then used for specialized
    subclasses.
    Args:
        - path (str): path to folder containing files
        - prefix (str): prefix of text and label files to load
        - vocab_size (int): maximum number of unique tokens to index
        - vocabulary (dict): maps tokens (str) to indices (int). If provided
            it is used instead of building it from the dataset, and
            vocab_size is ignored.
    """
    __slots__ = ['prefix', 'vocabulary', 'text_ids', 'labels']

    def __init__(self, path, prefix, process_fn, vocab_size=10000,
                 vocabulary=None):

        self.prefix = prefix
        token_counts = Counter()
        processed_tweets = []

        # Open text file with tweets
        print('Reading files in directory {}'.format(os.path.join(path, prefix)))
        with open(os.path.join(path, prefix + TEXT_EXT)) as file:
            for i, line in enumerate(file):
                # Tokenize and process line
                tokens = process_fn(line)
                processed_tweets.append(tokens)

                if vocabulary is None:
                    token_counts.update(tokens)

        print('Read file with {:d} tweets'.format(len(processed_tweets)))

        # Build vocabulary if not provided
        if vocabulary is None:
            print('Building vocabulary')
            vocabulary = defaultdict(lambda: len(vocabulary))
            _ = vocabulary[PAD_SYMBOL]
            _ = vocabulary[UNK_SYMBOL]
            for token, _ in token_counts.most_common(vocab_size):
                _ = vocabulary[token]
        else:
            print('Using vocabulary containing {:d} tokens'.format(
                len(vocabulary)))

        self.vocabulary = dict(vocabulary)

        # Store text in memory as word ids
        self.text_ids = []
        for tweet in processed_tweets:
            self.text_ids.append(list(map(
                lambda x: self.vocabulary.get(x, self.vocabulary[UNK_SYMBOL]),
                tweet)))

        # Load labels
        print('Loading labels')
        self.labels = np.empty(len(self.text_ids), dtype=np.int)
        with open(os.path.join(path, prefix + LABELS_EXT)) as file:
            for i, line in enumerate(file):
                self.labels[i] = int(line)

    def __getitem__(self, index):
        return (torch.tensor(self.text_ids[index], dtype=torch.long),
                torch.tensor(self.labels[index], dtype=torch.long), index)

    def __len__(self):
        return len(self.text_ids)

    @staticmethod
    def collate_fn(data_list):
        """
        Prepare a batch from a list of samples.
        Args:
            - data_list (list): contains tuples, each with two tensors
                as returned by __getitem__() in the Dataset class.
        Returns:
            - padded_data (tensor): padded sequences forming a batch
            - labels (tensor): batch of labels
            - lengths (tensor): length of each sequence in the batch
        """
        # Separate token indices and labels
        data, labels, indices = zip(*data_list)

        # Get length of each tensor
        lengths = np.array([len(tensor) for tensor in data])
        # Sort tensors from longest to shortest
        sorted_idx = np.argsort(lengths)[::-1]
        sorted_data = [data[idx] for idx in sorted_idx]
        sorted_labels = torch.stack([labels[idx] for idx in sorted_idx])
        sorted_lengths = torch.tensor(lengths[sorted_idx], dtype=torch.long)
        sorted_indices = [indices[idx] for idx in sorted_idx]

        # Create padded batch
        padded_data = pad_sequence(sorted_data)

        return padded_data, sorted_labels, sorted_lengths, sorted_indices

    def dump(self, filename):
        """ Save dataset to disk using the provided file name (str) """
        joblib.dump(self, filename)
        print('Dumped dataset to {}'.format(filename))

    @staticmethod
    def load(filename):
        """ Load a serialized dataset from the provided file name (str).
        Assumes file is a valid serialized dataset.
        """
        dataset = joblib.load(filename)
        print('Loaded dataset with {:d} tweets, {:d} unique tokens'.format(
            len(dataset), len(dataset.vocabulary)))
        return dataset


class TweetsBOWDataset(TweetsBaseDataset):
    """ A Dataset class for the emoji prediction task that stores tweets as
        bag of words.
    Args:
        - path (str): path to folder containing files
        - prefix (str): prefix of text and label files to load
        - vocab_size (int): maximum number of unique words to index
        - vocabulary (dict): maps tokens (str) to indices (int). If provided
            it is used instead of building it from the dataset, and
            vocab_size is ignored.
    """
    def __init__(self, path, prefix, vocab_size=10000, vocabulary=None):
        TweetsBaseDataset.__init__(self, path, prefix, vocab_size, vocabulary)

        # Using the vocabulary, build count matrix from text ids
        print('Loading counts matrix')
        count_matrix = lil_matrix((self.length, len(self.vocabulary)),
                                  dtype=np.int)
        for i, token_ids in enumerate(self.text_ids):
            # Count ids in tweet
            token_id_counter = Counter(token_ids)
            token_ids, counts = zip(*token_id_counter.items())
            count_matrix[i, token_ids] = counts

        # Add tf-idf weighting
        print('Creating TF-ID matrix')
        self.data = TfidfTransformer().fit_transform(count_matrix)

def get_mapping(filename):
    """Read a mapping from emoji IDs to character.
    Args:
        filename (str): location of the mapping file
    Returns: dict, mapping id (int) to character (str)
    """
    id_to_emoji = OrderedDict()
    with open(filename) as file:
        for line in file:
            values = line.split()
            id_to_emoji[int(values[0])] = values[1]
    return id_to_emoji

if __name__ == '__main__':
    # When run as a script all datasets are loaded, processed and serialized
    from ekphrasis.classes.preprocessor import TextPreProcessor
    from ekphrasis.classes.tokenizer import SocialTokenizer

    text_processor = TextPreProcessor(
        # terms that will be normalized
        normalize=['url', 'email', 'percent', 'money', 'phone', 'user',
                   'time', 'url', 'date', 'number'],
        # terms that will be annotated
        annotate={"hashtag", "allcaps", "elongated", "repeated",
                  'emphasis'},

        # corpus from which the word statistics are going to be used
        # for word segmentation
        segmenter="twitter",

        # corpus from which the word statistics are going to be used
        # for spell correction
        corrector="twitter",

        unpack_hashtags=True,  # perform word segmentation on hashtags
        unpack_contractions=True,  # Unpack contractions (can't -> can not)
        spell_correct_elong=False,  # spell correction for elongated words

        # select a tokenizer. You can use SocialTokenizer, or pass your own
        # the tokenizer, should take as input a string and return a list of tokens
        tokenizer=SocialTokenizer(lowercase=True).tokenize
    )

    data_dir = './data'
    train_set = TweetsBaseDataset(os.path.join(data_dir, 'train'), 'us_train',
                                  text_processor.pre_process_doc)
    train_set.dump(os.path.join(data_dir, 'train', 'us_train.set'))

    dev_set = TweetsBaseDataset(os.path.join(data_dir, 'dev'),
                                'us_trial', text_processor.pre_process_doc,
                                vocabulary=train_set.vocabulary)
    dev_set.dump(os.path.join(data_dir, 'dev', 'us_trial.set'))

    test_set = TweetsBaseDataset(os.path.join(data_dir, 'test'),
                                 'us_test', text_processor.pre_process_doc,
                                 vocabulary=train_set.vocabulary)
    test_set.dump(os.path.join(data_dir, 'test', 'us_test.set'))
