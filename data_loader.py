import os
import csv
import copy
import json
import logging
import random
import torch
from torch.utils.data import TensorDataset

from utils import get_label, pos_neg_pair

logger = logging.getLogger(__name__)


class InputExample(object):
    """
    A single training/test example for simple sequence classification.

    Args:
        guid: Unique id for the example.
        text_a: string. The untokenized text of the first sequence. For single
        sequence tasks, only this sequence must be specified.
        label: (Optional) string. The label of the example. This should be
        specified for train and dev examples, but not for test examples.
    """

    def __init__(self, guid, text_a, label):
        self.guid = guid
        self.text_a = text_a
        self.label = label


    def __repr__(self):
        return str(self.to_json_string())

    def to_dict(self):
        """Serializes this instance to a Python dictionary."""
        output = copy.deepcopy(self.__dict__)
        return output

    def to_json_string(self):
        """Serializes this instance to a JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


class InputFeatures(object):
    """
    A single set of features of data.

    Args:
        input_ids: Indices of input sequence tokens in the vocabulary.
        attention_mask: Mask to avoid performing attention on padding token indices.
            Mask values selected in ``[0, 1]``:
            Usually  ``1`` for tokens that are NOT MASKED, ``0`` for MASKED (padded) tokens.
        token_type_ids: Segment token indices to indicate first and second portions of the inputs.
    """

    def __init__(self, input_ids, attention_mask, token_type_ids, label_id,
                 e1_mask, e2_mask, e1_id, e2_id):
        self.input_ids = input_ids
        self.attention_mask = attention_mask
        self.token_type_ids = token_type_ids
        self.label_id = label_id
        self.e1_mask = e1_mask
        self.e2_mask = e2_mask
        self.e1_id = e1_id
        self.e2_id = e2_id

    def __repr__(self):
        return str(self.to_json_string())

    def to_dict(self):
        """Serializes this instance to a Python dictionary."""
        output = copy.deepcopy(self.__dict__)
        return output

    def to_json_string(self):
        """Serializes this instance to a JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


class SemEvalProcessor(object):
    """Processor for the Semeval data set """

    def __init__(self, args):
        self.args = args
        self.relation_labels = get_label(args)

    @classmethod
    def _read_tsv(cls, path, file=None):
        """Reads a tab separated value file."""
        """
        Args:
            path: the path of tsv file to read
            file: filename
        """
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t", quotechar=file)
            lines = []
            for line in reader:
                lines.append(line)
            return lines

    def _create_examples(self, lines, mode):

        """Creates examples for the training and dev sets."""
        """
        Args:
            mode: train, dev, test
        """
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (mode, i)
            text_a = line[1]
            label = self.relation_labels.index(line[0])

            if i % 1000 == 0:
                logger.info(line)
            examples.append(InputExample(guid=guid, text_a=text_a, label=label))
        print("create example finish!")
        return examples

    def get_examples(self, mode):
        """
        Args:
            mode: train, dev, test
        """
        file_to_read = None
        if mode == 'train':
            file_to_read = "train.tsv"
        elif mode == 'test':
            file_to_read = "test.tsv"
            
        logger.info("LOOKING AT {}".format(os.path.join(self.args.data_dir, file_to_read)))
        return self._create_examples(self._read_tsv(os.path.join(self.args.data_dir, file_to_read)), mode)

class TacredProcessor(object):
    """Processor for the SemEval-2010 Task 8 data set """

    def __init__(self, args):
        self.args = args
        self.relation_labels = get_label(args)


    @classmethod
    def _read_tsv(cls, input_file, quotechar=None):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t", quotechar=quotechar)
            lines = []
            for line in reader:
                lines.append(line)
            return lines
    
    def _preprocess_example(self,text_a):
        for i,text in enumerate(text_a):
            flag = True
            if len(text) >= 5:
                length_text = len(text) - 1
                index = 0
                while (index < length_text - 1):
                    if text[index] != text[index + 1]:
                        flag=False
                        break
                    else:
                        index += 1
                if flag:
                    text_a[i] = text[0:3]
        return text_a
    
    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            line = json.loads(line[0])
            text_a = line['tokens']
            text_a = self._preprocess_example(text_a)
            
            label = self.relation_labels.index(line['label'])
            entity_pos = line['entities']

            if entity_pos[0][0] > entity_pos[0][1]:
                tmp = entity_pos[0][0]
                entity_pos[0][0] = entity_pos[0][1]
                entity_pos[0][1] = tmp
            if entity_pos[1][0] > entity_pos[1][1]:
                tmp = entity_pos[1][0]
                entity_pos[1][0] = entity_pos[1][1]
                entity_pos[1][1] = tmp
            entity1_start, entity1_end = entity_pos[0][0], entity_pos[0][1] 
            entity2_start, entity2_end = entity_pos[1][0], entity_pos[1][1]
            
            
            if entity1_start < entity2_start :     
                text_a.insert(entity1_start, '<e1>')
                text_a.insert(entity1_end+1, '</e1>')
                text_a.insert(entity2_start+2, '<e2>')
                text_a.insert(entity2_end+3,'</e2>')
            else:
                text_a.insert(entity2_start, '<e2>')
                text_a.insert(entity2_end+1, '</e2>')
                text_a.insert(entity1_start+2, '<e1>')
                text_a.insert(entity1_end+3,'</e1>')
            text = ' '.join([text_a[i] for i in range(len(text_a))])
            examples.append(InputExample(guid=guid, text_a=text, label=label))
        return examples

    def get_examples(self, mode):
        """
        Args:
            mode: train, dev, test
        """
        file_to_read = None
        if mode == 'train':
            file_to_read = "train.jsonl"
        elif mode == 'test':
            file_to_read = "test.jsonl"
        logger.info("LOOKING AT {}".format(os.path.join(self.args.data_dir, file_to_read)))
        return self._create_examples(self._read_tsv(os.path.join(self.args.data_dir, file_to_read)), mode)

processors = {
    "semeval": SemEvalProcessor,
    "tacred": TacredProcessor
}

def convert_examples_to_features(examples, args, tokenizer,
                                 cls_token='[CLS]',
                                 cls_token_segment_id=0,
                                 sep_token='[SEP]',
                                 pad_token=0,
                                 pad_token_segment_id=0,
                                 sequence_a_segment_id=0,
                                 mask_padding_with_zero=True):
    '''
    :param examples: the examples of dataset
    :param args: parameters
    :param tokenizer:tokenizer
    :param cls_token: '[CLS]' marker
    :param cls_token_segment_id: The default is 0 if there is a sentence only
    :param sep_token:'[SEP]' marker
    :param pad_token: padding token,default is 0
    :return: features(InputFeatures)
    '''
    features = []
    max_seq_len = args.max_seq_len
    entity2id = {}
    for (ex_index, example) in enumerate(examples):
        if ex_index % 5000 == 0:
            logger.info("Writing example %d of %d" % (ex_index, len(examples)))

        e11_p_ = example.text_a.index("<e1>")+5  # the start position of entity1
        e12_p_ = example.text_a.index("</e1>")  # the end position of entity1
        e21_p_ = example.text_a.index("<e2>")+5 # the start position of entity2
        e22_p_ = example.text_a.index("</e2>")  # the end position of entity2
        e1 = example.text_a[e11_p_:e12_p_].strip()
        e2 = example.text_a[e21_p_:e22_p_].strip()


        if not entity2id.__contains__(e1):
            e1_id = len(entity2id)
            entity2id[e1] = e1_id
        else:
            e1_id = entity2id[e1]
        if not entity2id.__contains__(e2):
            e2_id = len(entity2id)
            entity2id[e2] = e2_id
        else:
            e2_id = entity2id[e2]


        tokens_a = tokenizer.tokenize(example.text_a)
        e11_p = tokens_a.index("<e1s>")  # the start position of entity1
        e12_p = tokens_a.index("<e1e>")  # the end position of entity1
        e21_p = tokens_a.index("<e2s")  # the start position of entity2
        e22_p = tokens_a.index("<e2>e")  # the end position of entity2


        # Add 1 because of the [CLS] token
        e11_p += 1
        e12_p += 1
        e21_p += 1
        e22_p += 1

        # Account for [CLS] and [SEP] with "- 2" and with "- 3" for RoBERTa.
        special_tokens_count = 2
        if len(tokens_a) > max_seq_len - special_tokens_count:
            tokens_a = tokens_a[:(max_seq_len - special_tokens_count)]

        tokens = tokens_a
        tokens += [sep_token]

        token_type_ids = [sequence_a_segment_id] * len(tokens)

        tokens = [cls_token] + tokens
        token_type_ids = [cls_token_segment_id] + token_type_ids

        input_ids = tokenizer.convert_tokens_to_ids(tokens)

        # The mask has 1 for real tokens and 0 for padding tokens. Only real
        # tokens are attended to.
        attention_mask = [1 if mask_padding_with_zero else 0] * len(input_ids)

        # Zero-pad up to the sequence length.
        padding_length = max_seq_len - len(input_ids)
        input_ids = input_ids + ([pad_token] * padding_length)
        attention_mask = attention_mask + ([0 if mask_padding_with_zero else 1] * padding_length)
        token_type_ids = token_type_ids + ([pad_token_segment_id] * padding_length)

        # e1 mask, e2 mask
        e1_mask = [0] * len(attention_mask)
        e2_mask = [0] * len(attention_mask)

        for i in range(e11_p+1, e12_p):
            e1_mask[i] = 1
        for i in range(e21_p+1, e22_p):
            e2_mask[i] = 1


        assert len(input_ids) == max_seq_len, "Error with input length {} vs {}".format(len(input_ids), max_seq_len)
        assert len(attention_mask) == max_seq_len, "Error with attention mask length {} vs {}".format(len(attention_mask), max_seq_len)
        assert len(token_type_ids) == max_seq_len, "Error with token type length {} vs {}".format(len(token_type_ids), max_seq_len)

        label_id = int(example.label)
        

        if ex_index < 5:
            logger.info("*** Example ***")
            logger.info("guid: %s" % example.guid)
            logger.info("tokens: %s" % " ".join([str(x) for x in tokens]))
            logger.info("input_ids: %s" % " ".join([str(x) for x in input_ids]))
            logger.info("attention_mask: %s" % " ".join([str(x) for x in attention_mask]))
            logger.info("token_type_ids: %s" % " ".join([str(x) for x in token_type_ids]))
            logger.info("label: %s (id = %d)" % (example.label, label_id))
            logger.info("e1_mask: %s" % " ".join([str(x) for x in e1_mask]))
            logger.info("e2_mask: %s" % " ".join([str(x) for x in e2_mask]))
            logger.info("e1_id: %d" % e1_id)
            logger.info("e2_id: %d" % e2_id)

        features.append(
            InputFeatures(input_ids=input_ids,
                          attention_mask=attention_mask,
                          token_type_ids=token_type_ids,
                          label_id=label_id,
                          e1_mask=e1_mask,
                          e2_mask=e2_mask,
                          e1_id=e1_id,
                          e2_id=e2_id))
    return features


def load_and_cache_examples(args, tokenizer, mode):
    '''
        load examples from cache file
        :param args:  args
        :param tokenizer:
        :param mode: Option is "train","test","dev","eval"
        :return: dataset
    '''
    processor = processors[args.task](args)

    # Load data features from cache or dataset file
    cached_features_file = os.path.join(
        args.data_dir,
        'cached_{}_{}_{}_{}'.format(
            mode,
            args.task,
            list(filter(None, args.model_name_or_path.split("/"))).pop(),
            args.max_seq_len
        )
    )
    label_list = get_label(args)
    num_labels = len(label_list)
    if os.path.exists(cached_features_file):
        logger.info("Loading features from cached file %s", cached_features_file)
        features = torch.load(cached_features_file)
    else:
        logger.info("Creating features from dataset file at %s", args.data_dir)
        if mode == "train":
            examples = processor.get_examples("train")
        elif mode == "dev":
            examples = processor.get_examples("dev")
        elif mode == "test":
            examples = processor.get_examples("test")
        else:
            raise Exception("For mode, Only train, dev, test is available")
        features = convert_examples_to_features(examples, args, tokenizer)
        logger.info("Saving features into cached file %s", cached_features_file)
        torch.save(features, cached_features_file)
    dataset = []
    if mode == "train":
        features_subs=pos_neg_pair(num_labels, features, args)
        for features_sub in features_subs:
            sub_input_ids = torch.tensor([f.input_ids for f in features_sub], dtype=torch.long)
            sub_attention_mask = torch.tensor([f.attention_mask for f in features_sub], dtype=torch.long)
            sub_token_type_ids = torch.tensor([f.token_type_ids for f in features_sub], dtype=torch.long)
            sub_e1_mask = torch.tensor([f.e1_mask for f in features_sub], dtype=torch.long)  # add e1 mask
            sub_e2_mask = torch.tensor([f.e2_mask for f in features_sub], dtype=torch.long)  # add e2 mask
            sub_e1_id = torch.tensor([f.e1_id for f in features_sub], dtype=torch.long)
            sub_e2_id = torch.tensor([f.e2_id for f in features_sub], dtype=torch.long)
            sub_label_ids = torch.tensor([f.label_id for f in features_sub], dtype=torch.long)
            sub_dataset = TensorDataset(sub_input_ids, sub_attention_mask, sub_token_type_ids, sub_label_ids, sub_e1_mask, sub_e2_mask, sub_e1_id, sub_e2_id)
            dataset.append(sub_dataset)
        return dataset
    else:
        all_input_ids = torch.tensor([f.input_ids for f in features], dtype=torch.long)
        all_attention_mask = torch.tensor([f.attention_mask for f in features], dtype=torch.long)
        all_token_type_ids = torch.tensor([f.token_type_ids for f in features], dtype=torch.long)
        all_e1_mask = torch.tensor([f.e1_mask for f in features], dtype=torch.long)  # add e1 mask
        all_e2_mask = torch.tensor([f.e2_mask for f in features], dtype=torch.long)  # add e2 mask
        all_e1_id = torch.tensor([f.e1_id for f in features], dtype=torch.long)
        all_e2_id = torch.tensor([f.e2_id for f in features], dtype=torch.long)
        all_label_ids = torch.tensor([f.label_id for f in features], dtype=torch.long)
        dataset = TensorDataset(all_input_ids, all_attention_mask, all_token_type_ids,
                                 all_label_ids, all_e1_mask, all_e2_mask, all_e1_id, all_e2_id)
        return dataset
