import inflection

from collections import defaultdict

from grammar import Grammar
from verbnet import VerbNet, XTAGMapper
from propbank import Propbank
from derivation import DerivationTree
from semantics import Semantics, VariableFactory, Constant, Relation, Token
from tagtree import SemTree

class SemTreeGrammar(object):
    """
    Class storing a grammar of semantically annotated XTAG trees, whose
    semantics were derived by mapping VerbNet frames to declarative trees and
    then doing transformations for:
        wh-movement
        PRO
        gerunds
        relative clauses
    """

    def __init__(self, grammar, verbnet, xtag_mapper, propbank):
        self.verbnet = verbnet
        self.grammar = grammar
        self.xtag_mapper = xtag_mapper
        self.propbank = propbank

    def get_semtree(self, tree_name, anchor, lemma=None, pb_instance=None):
        tree = self.grammar.get(tree_name)
        if not tree.belongs_to_verb_family():
            return self.get_nonverb_semtree(tree_name, anchor)

        if pb_instance is not None:
            verb_trees = self.get_semtrees_from_pb_instance(tree_name, anchor, pb_instance)
        elif lemma is not None:
            verb_trees = self.get_semtrees_from_lemma(tree_name, anchor, lemma)
        else:
            assert False

        # Don't have any better way to choose at this point 
        return verb_trees[0] 

    def get_semtrees_from_lemma(self, tree_name, anchor, lemma):
        frames = self.verbnet.get_frames(lemma)
        semtrees = [self.add_semantics(f, tree_name, lemma) for f in frames]
        semtrees = [s for s in semtrees if s is not None]
        return semtrees

    def get_semtrees_from_pb_instance(self, tree_name, anchor, pb_instance):
        vn_classes = self.propbank.get_vn_classes(pb_instance.filenum, pb_instance.sentnum, pb_instance.word)
        frames = []
        for vn_class in vn_classes:
            frames += self.verbnet.get_frames_from_class(vn_class)
        semtrees = [self.add_semantics(f, tree_name, anchor) for f in frames]
        semtrees = [s for s in semtrees if s is not None]
        return semtrees

    def add_semantics(self, frame, tree_name, anchor):
        """
        Given a lemma and tree names, returns sem trees given by all matching
        verb classes and their frames. This is where all of the transformation
        logic currently lives for how to compute the semantics for combinations 
        of wh/PRO/gerunds/relclauses. These essentially act as 'metagrammar rules'
        that can be applied successively.
        """

        tree = self.grammar.get(tree_name)
        declarative_tree = self.grammar.get_declarative_tree(tree.tree_family)
        assert declarative_tree is not None
        sub_nouns = [n for n in declarative_tree.subst_nodes() if n.prefix() == "NP"]

        # Going to lexicalize for each frame
        tree = tree.copy()

        xtag_family = self.xtag_mapper.get_xtag_family(frame.primary, frame.secondary) 
        if xtag_family is None or xtag_family != tree.tree_family:
            return None

        # Currently ignore trees with more than one anchor (like Tnx0VPnx1)
        if len(tree.anchor_positions()) > 1:
            return None

        # Can't align semantics if wrong number of nouns/subnodes
        if len(frame.np_var_order) != len(sub_nouns):
            return None

        # Lexicalize tree
        tree.lexicalize(anchor)

        # Align np vars and substitution nodes
        node_entity_dict = {}
        for np_var, subst_node in zip(frame.np_var_order, sub_nouns):
            node_entity_dict[subst_node.label()] = np_var

        tree = SemTree.convert(tree)

        # Map event semantics to root
        sem_dict = frame.sem_dict
        tree.semantics = sem_dict["Event"]
        tree.sem_var = tree.semantics.event()
        # Map argument semantics to subst nodes
        for node_label, np_var in node_entity_dict.items():
            subst_node = tree.find(node_label)
            if subst_node is not None:
                subst_node.semantics = sem_dict[np_var.name]
                subst_node.sem_var = np_var

        # Check for PRO trees
        # Unclear to me how to handle the semantics here
        # The "PRO" noun should be replaced by a noun in the tree that this
        # would be substituted into. Probably need to handle during subst.
        if "PRO" in tree.tree_name:
            nps = [n for n in tree.subtrees() if n.prefix() == "NP"]
            pro_np = [n for n in nps if n.has_pro()][0]
            control_np = [n for n in nps if n.has_control()][0]

        # Relative Clauses 
        # In a relative clause, the root and and foot both represent the 
        # variable that was extracted e.g. in "cat -> cat that chased the dog"
        # both "cat" and "cat that chased the dog" refer to the cat entity
        if tree.tree_name.startswith("betaN"):
            nps = [n for n in tree.subtrees() if n.prefix() == "NP" and n.label() not in ["NP_r", "NP_f", "NP_w"]]
            extracted = [n for n in nps if n.has_trace()][0] 
            tree.find("NP_r").sem_var = node_entity_dict[extracted.label()]
            tree.find("NP_f").sem_var = node_entity_dict[extracted.label()]
            wh_var = VariableFactory.get_var()
            tree.find("NP_w").sem_var = wh_var

        return tree

    def get_tree_families(self, lemma):
        """Returns all tree families that can be associated with a lemma"""
        tree_families = set()
        frames = self.verbnet.get_frames(lemma)
        for f in frames:
            xtag_family = self.xtag_mapper.get_xtag_family(f.primary, f.secondary) 
            if xtag_family is not None:
                tree_families.add(xtag_family)
        return tree_families

    def get_nonverb_semtree(self, tree_name, anchor):
        """
        Returns the semantically annotated tree specified by tree_name anchored
        by anchor. Note: the semantic info should eventually live somewhere
        that is more flexible (json, xml, etc)
        """

        tree = self.grammar.get(tree_name)
        tree.lexicalize(anchor)

        if tree.initial():
            v = VariableFactory.get_var(pre=anchor[0])
        else:
            v = VariableFactory.get_var()

        if tree_name in ["alphaNXN", "betaAn", "betaNn"]:
            con = Constant(inflection.titleize(anchor))
            rel = Relation("ISA", [v, con])
            s = Semantics([rel])
            tree = SemTree.convert(tree)
            tree.semantics = s
            tree.sem_var = v
        elif tree_name == "betaDnx" and anchor in ["a", "an", "the", "one"]:
            s = Semantics([])
            s.set_quantification(v, Token.EXISTS)
            node_entity_dict = {s.label(): v for s in tree.subtrees()}
            tree = SemTree.convert(tree)
            tree.semantics = s
            tree.sem_var = v
        else:
            print(tree_name, anchor)
            raise NotImplementedError

        return tree

if __name__ == '__main__':
    '''
    g = Grammar.load()
    vnet = VerbNet.load()
    mapper = XTAGMapper.load()
    propbank = Propbank.load()
    s = SemTreeGrammar(g, vnet, mapper, propbank)
    print(len(propbank.instance_dict))

    chase_ps = s.get_semtree('alphanx0Vnx1', 'chased', lemma='chase')
    dog_ps = s.get_semtree('alphaNXN', 'dog')
    cat_ps = s.get_semtree('alphaNXN', 'cat')
    red_ps = s.get_semtree('betaAn', 'red')
    pet_ps = s.get_semtree('betaNn', 'pet')
    the_ps = s.get_semtree('betaDnx', 'a')
    ps = chase_ps.substitute(dog_ps, "NP_0")
    ps = ps.substitute(cat_ps, "NP_1")
    ps = ps.adjoin(red_ps, "N")
    ps = ps.adjoin(pet_ps, "N-1")
    ps = ps.adjoin(the_ps, "NP_0")
    print(ps)
    ps.tree.draw()
    print()

    deriv_trees = DerivationTree.load_all()

    tree_families = set(mapper.xtag_mapping.values())
    treeset = set([
        "alphaNXN",
        "betaAn",
        "betaNn",
        "betaDnx"

    ])
    deriv_trees = [d for d in deriv_trees if d.have_semantics(g, tree_families, treeset)]
    print(len(deriv_trees))
    d = deriv_trees[6]
    print(d.file_num, d.sentence_num, d.anchor)
    parse_tree = d.get_parse_tree(s)
    '''

    g = Grammar.load()
    vnet = VerbNet.load()
    mapper = XTAGMapper.load()
    propbank = Propbank.load()
    s = SemTreeGrammar(g, vnet, mapper, propbank)
    chase_ps = s.get_semtree('alphanx0Vnx1', 'chase', lemma='chase')
    cat_ps = s.get_semtree('alphaNXN', 'cat')
    dog_ps = s.get_semtree('alphaNXN', 'dog')
    red_ps = s.get_semtree('betaAn', 'red')
    the_ps = s.get_semtree('betaDnx', 'a')
    chase_ps = chase_ps.substitute(cat_ps, 'NP_0')
    chase_ps = chase_ps.substitute(dog_ps, 'NP_1')
    chase_ps = chase_ps.adjoin(red_ps, "N")
    chase_ps = chase_ps.adjoin(the_ps, 'NP_0')
    for sub in chase_ps.subtrees():
        print(sub.label(), sub.semantics)
    
    deriv_trees = DerivationTree.load_all()
    tree_families = set(mapper.xtag_mapping.values())
    treeset = set([
        "alphaNXN",
        "betaAn",
        "betaNn",
        "betaDnx"

    ])
    deriv_trees = [d for d in deriv_trees if d.have_semantics(g, tree_families, treeset)]
    print(len(deriv_trees))
    d = deriv_trees[0]
    print(d.file_num, d.sentence_num, d.anchor)
    parse_tree = d.get_parse_tree(s)

    