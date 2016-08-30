import glob, json, nltk, os, pickle, re
from collections import deque
from vnet_constants import DATA_DIR

class DerivationTree(nltk.Tree):
    """
    Class representing a tree (either initial or auxiliary) in the XTAG grammar
    Label specified as "prefix_suffix-renamesuffix", i.e. "NP_0-1"
    """
    def __init__(self, label, children=None, filename=None):
        if children is None:
            children = []
        self._label = label
        self.tree_name, self.anchor, self.location = DerivationTree.label_to_tree_word_loc(label)
        self.file_num, self.sentence_num = DerivationTree.filename_to_file_sent_num(filename)
        self.filename = filename
        nltk.Tree.__init__(self, self._label, children)

    def have_semantics(self, grammar, tree_families, tree_set):
        """Returns True if every elem tree in self is in tree_set (annotated)"""
        trees = [grammar.get(s.tree_name) for s in self.subtrees()]
        return all(t is not None and (t.tree_family in tree_families or t.tree_name in tree_set) for t in trees)

    def get_parse_tree(self, semgrammar, depth=0):
        if semgrammar.grammar.get(self.tree_name, copy=False).belongs_to_verb_family():
            pb_instance = semgrammar.propbank.get_instance(self.file_num, self.sentence_num, self.anchor)
        else:
            pb_instance = None

        semtree = semgrammar.get_semtree(self.tree_name, self.anchor, pb_instance=pb_instance)
        for s in semtree.subtrees():
            s.deriv_depth = depth

        for c in self:
            try:
                c_semtree = c.get_parse_tree(semgrammar, depth + 1)

                if 'alpha' in c.tree_name:
                    sub_nodes = [s for s in semtree.subst_nodes() if s.original_label() == c.location and s.deriv_depth == depth]
                    assert len(sub_nodes) == 1
                    sub_node = sub_nodes[0]
                    semtree.substitute(c_semtree, sub_node.label())
                elif 'beta' in c.tree_name:
                    adj_nodes = [s for s in semtree.subtrees() if s.original_label() == c.location and s.deriv_depth == depth]
                    assert len(adj_nodes) == 1
                    adj_node = adj_nodes[0]
                    semtree.adjoin(c_semtree, adj_node.label())

            except IndexError:
                #print("CANNOT FIND TREES ERROR")
                continue
            except NotImplementedError:
                #print("NOT IMPLEMENTED HELPER TREE ERROR")
                continue
            except KeyError:
                #print("KEY ERROR FOR FINDING ROLE")
                continue
            except AttributeError:
                #print("ATTRIBUTE ERROR IN PERFORMING ADJUNCTION")
                continue

        return semtree

    @classmethod
    def convert(cls, val, filename=None):
        """Returns an nltk.Tree converted to a DerivationTree"""
        if isinstance(val, nltk.Tree):
            children = [cls.convert(child, filename=filename) for child in val]
            return cls(val._label, children=children, filename=filename)
        elif isinstance(val, str):
            return cls(val, filename=filename)

    @classmethod
    def from_file(cls, filename):
        tree_dict = json.load(open(filename, 'r'))
        if 'deriv' not in tree_dict or tree_dict['deriv'] == 'None':
            return None
        deriv_tree_str = tree_dict['deriv']
        deriv_tree = nltk.Tree.fromstring(deriv_tree_str)
        deriv_tree = DerivationTree.convert(deriv_tree, filename=filename)
        return deriv_tree

    @classmethod
    def label_to_tree_word_loc(cls, label):
        """
        Takes a deriv tree label and returns its components:
            tree_name[anchor]<action_location>, e.g. alphaNXN[chairman]<NP_1>
        """
        tree_name = re.search('(.*)\[', label).group(1)
        word = re.search('\[(.*?)\]', label).group(1)
        loc_match = re.search('\<(.*?)\>', label)
        loc = loc_match.group(1) if loc_match is not None else None
        return tree_name, word, loc

    @classmethod
    def prune_deriv_tree(cls, grammar, deriv_tree, tree_families, tree_set):
        """
        Returns a derivation tree with branches pruned at any tree without semantics

        This is a strategy to use more of the trees output from the parser. The hope
        is that essential trees precede non-essential trees in the derivation, so
        we can still recover most of the semantics by pruning.
        """

        queue = deque([[deriv_tree, None]])

        while len(queue) > 0:
            t, parent = queue.popleft()

            if grammar.get_tree_family(t.tree_name) not in tree_families and t.tree_name not in tree_set:
                if parent is None:
                    return None
                else:
                    del parent[parent.index(t)]
            
            elif isinstance(t, nltk.Tree):
                queue += [[c, t] for c in t]

        return deriv_tree

    @classmethod
    def filename_to_file_sent_num(cls, filename):
        """Filename of form: ../grammars/parse_trees/wsj_0001_0.txt"""
        if filename is None:
            return "", ""
        else:
            filename = filename.split("/")[-1].split(".")[0].replace("wsj_", "")
            file_num, sent_num = filename.split("_")
            return file_num, sent_num

    @classmethod
    def load_all(cls, treedir=DATA_DIR + 'parse_trees'):
        pickle_filename = DATA_DIR + 'derivation.pickle'
        if os.path.exists(pickle_filename):
            return pickle.load(open(pickle_filename, 'rb'))
        else:
            deriv_trees = [DerivationTree.from_file(f) for f in glob.glob(treedir + '/*')]
            deriv_trees = [d for d in deriv_trees if d is not None]
            pickle.dump(deriv_trees, open(pickle_filename, 'wb'))
            return deriv_trees
