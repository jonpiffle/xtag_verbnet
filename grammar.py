import pickle, os, xmltodict

from collections import defaultdict

from vnet_constants import DATA_DIR
from tagtree import TAGTree

class Grammar(object):
    """
    Class for representing the XTAG Grammar. Loads grammar from disk, where it
    may be cached or require XML parsing. Provides an interface to return a 
    specific tree (given a name) or a declarative tree (given a family name)
    """

    def __init__(self, trees):
        self.tree_dict = {t.tree_name: t for t in trees}
        self.anchor_pos_dict = defaultdict(list)
        self.tree_family_dict = defaultdict(list)
        for t in trees:
            self.anchor_pos_dict[tuple([a.prefix() for a in t.anchor_positions()])].append(t)
            self.tree_family_dict[t.tree_family].append(t)

    def get(self, tree_name, copy=True):
        """Returns the TAGTree given by tree_name"""
        tree = self.tree_dict.get(tree_name)
        if tree is not None and copy:
            tree = tree.copy()
        return tree

    def get_trees_from_tree_family(self, tree_family, copy=True):
        trees = self.tree_family_dict.get(tree_family)
        if trees is not None and copy:
            trees = [t.copy() for t in trees]
        return trees

    def get_trees_from_anchor_pos(self, pos, copy=True):
        if isinstance(pos, str):
            pos = tuple([pos])
        trees = self.anchor_pos_dict.get(pos)
        if trees is not None and copy:
            trees = [t.copy() for t in trees]
        return trees

    def filter(self, treeset):
        """Removes any trees not in treeset from grammar"""
        # Update tree dict
        self.tree_dict = {n:t for n,t in self.tree_dict.items() if n in treeset}
        return self

    def get_declarative_tree(self, family_name):
        """
        Returns the declarative tree associated with the given tree family. 
        This is typically an initial tree (given by replacing "T" with "alpha" 
        in the family name), but for some tree families is an auxiliary tree
        (given by replacing "T" with "beta").
        """
        alpha_tree_name = "alpha" + family_name[1:]
        beta_tree_name = "beta" + family_name[1:]
        tree = self.get(alpha_tree_name)
        if tree is None:
            tree = self.get(beta_tree_name)
        return tree

    @classmethod
    def fromxml(cls, filename=DATA_DIR+'xtag.xml'):
        """Returns a grammar given an XML XTAG representation"""
        with open(filename, 'r') as f:
            xml_string = f.read().strip()
        d = xmltodict.parse(xml_string)
        trees = []
        for entry in d['grammar']['entry']:
            trees.append(TAGTree.from_dict(entry))
        return Grammar(trees)

    @classmethod
    def load(cls, xml_filename=DATA_DIR + 'xtag.xml'):
        """Returns a grammar from cache if exists, else from XML"""
        grammar_file = DATA_DIR + 'xtag.pickle'
        if os.path.exists(grammar_file):
            return pickle.load(open(grammar_file, 'rb'))
        else:
            grammar = Grammar.fromxml(xml_filename)
            pickle.dump(grammar, open(grammar_file, 'wb'))
            return grammar
