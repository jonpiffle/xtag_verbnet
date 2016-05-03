import nltk, os, pickle

from collections import defaultdict
from nltk.corpus.reader import CategorizedBracketParseCorpusReader, PropbankCorpusReader
from nltk.corpus.util import LazyCorpusLoader
from nltk.corpus import propbank

from vnet_constants import DATA_DIR

class Propbank(object):
    """
    Class representing the Propbank corpus. Stores the specific WSJ annotations
    as PropbankInstances and stores that general verbframe information as roles.
    Provides an interface to access both of these
    """

    def __init__(self, role_dict, instance_dict):
        self.role_dict = role_dict
        self.instance_dict = instance_dict

    def get_role(self, roleset_id):
        """Returns role given roleset_id"""
        return self.role_dict[roleset_id]

    def get_instance(self, file_num, sent_num, word):
        return self.instance_dict[(file_num, sent_num)].get(word)

    def get_vn_classes(self, file_num, sent_num, word):
        instance = self.get_instance(file_num, sent_num, word)
        if instance is None:
            return []
        roleset_id = instance.roleset_id
        role = self.get_role(roleset_id)
        return role.vn_classes
   
    @classmethod
    def from_nltk(cls):
        """Returns a fully populated Propbank with the help of NLTK's interface"""
        ptb = LazyCorpusLoader(
            'ptb',
            CategorizedBracketParseCorpusReader,
            r'wsj/\d\d/wsj_\d\d\d\d.mrg',
            cat_file='allcats.txt'
        )

        propbank_ptb = LazyCorpusLoader(
            'propbank', PropbankCorpusReader,
            'prop.txt', 'frames/.*\.xml', 'verbs.txt',
            lambda filename: filename.upper(),
            ptb
        ) # Must be defined *after* ptb corpus.

        role_dict = {}
        for roleset_xml in propbank_ptb.rolesets():
            role = Role.fromxml(roleset_xml)
            role_dict[role.roleset_id] = role

        instance_dict = defaultdict(dict)
        pb_instances = propbank_ptb.instances()
        for instance in pb_instances:
            instance.fileid = instance.fileid.lower()
            file_num = instance.fileid.split("/")[-1].split(".")[0].replace("wsj_", "")
            sentnum = str(instance.sentnum)
            predicate = instance.predicate
            tree = instance.tree

            if isinstance(predicate, nltk.corpus.reader.propbank.PropbankTreePointer):
                key = Propbank.pointer_to_word(predicate, tree)
            elif isinstance(predicate, nltk.corpus.reader.propbank.PropbankSplitTreePointer):
                key = tuple([Propbank.pointer_to_word(p, tree) for p in predicate.pieces])
            else:
                ### TODO: Investigate when this is the case ###
                #assert False
                continue

            pb_instance = PropbankInstance(instance.fileid, file_num, sentnum, key, instance.roleset, instance.arguments)
            instance_dict[(file_num, sentnum)][key] = pb_instance

        return Propbank(role_dict, instance_dict)

    @classmethod
    def pointer_to_word(cls, pointer, tree):
        """
        Given a PropbankPointer (basically a special tree address), returns the 
        word at that location in the given tree
        """
        treepos = pointer.treepos(tree)
        word = tree[treepos].leaves()[0]
        return word

    @classmethod
    def load(cls):
        """Returns Propbank from cache if exists, else loads"""
        pickle_filename = DATA_DIR + 'propbank.pickle'
        if os.path.exists(pickle_filename):
            return pickle.load(open(pickle_filename, 'rb'))
        else:
            propbank = Propbank.from_nltk()
            pickle.dump(propbank, open(pickle_filename, 'wb'))
            return propbank

class PropbankInstance(object):
    """
    This is basically just a replica of the same class in nltk; however that
    class doesn't play nicely with pickle, and loading without pickle takes too long
    """
    def __init__(self, fileid, filenum, sentnum, word, roleset_id, arguments):
        self.fileid = fileid
        self.filenum = filenum
        self.sentnum = sentnum
        self.word = word
        self.roleset_id = roleset_id
        self.arguments = arguments

    def numbered_args(self):
        return [(ptr, arg) for ptr, arg in self.arguments if arg[-1].isdigit()]

class Role(object):
    """Represents a verb frame in Propbank"""
    def __init__(self, roleset_id, name, vncls_str):
        self.lemma = roleset_id.split(".")[0]
        self.roleset_id = roleset_id
        self.name = name
        self.vn_classes = vncls_str.split()

    @classmethod
    def fromxml(cls, xml):
        """Parses a role from the propbank xml file"""
        attrib = xml.attrib
        return Role(attrib['id'], attrib['name'], attrib.get('vncls', ''))
