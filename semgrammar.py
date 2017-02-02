import inflection, traceback, json

from collections import defaultdict

from grammar import Grammar
from verbnet import VerbNet, XTAGMapper
from propbank import Propbank
from derivation import DerivationTree
from semantics import Semantics, VariableFactory, Constant, Relation, Token, Variable, VariableBinding
from tagtree import SemTree
from semparser import SemanticParser, VariableParser
from vnet_constants import DATA_DIR

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
        self.sem_trees = {}

    def get_semtree(self, tree_name, anchor, lemma=None, pb_instance=None):
        if (tree_name, anchor) in self.sem_trees:
            return self.sem_trees[(tree_name, anchor)].copy()

        tree = self.grammar.get(tree_name)
        if len(tree.anchor_positions()) > 1:
            #print("NotImplementedError", tree.tree_family)
            raise NotImplementedError
        elif not tree.belongs_to_verb_family():
            sem_tree = self.get_nonverb_semtree(tree_name, anchor)
        elif tree.tree_family in ['Ts0N1', 'Tnx0Pnx1', 'Tnx0N1', 'Tnx0BEnx1', 'Tnx0Ax1', 'Ts0Ax1', 'Ts0Pnx1']:
            verb_trees = self.get_nonverb_tree_family(tree_name, anchor)
            sem_tree = verb_trees[0]
        elif pb_instance is not None:
            verb_trees = self.get_semtrees_from_pb_instance(tree_name, anchor, pb_instance)
            sem_tree = verb_trees[0] # Don't have any better way to choose at this point 
        elif lemma is not None:
            verb_trees = self.get_semtrees_from_lemma(tree_name, anchor, lemma)
            sem_tree = verb_trees[0] # Don't have any better way to choose at this point 
        else:
            #print("NotImplementedError", tree.tree_family)#, tree_name, anchor, lemma, pb_instance)
            raise NotImplementedError

        self.sem_trees[(tree_name, anchor)] = sem_tree
        return sem_tree.copy()

    def get_semtrees_from_lemma(self, tree_name, anchor, lemma):
        frames = self.verbnet.get_frames(lemma)
        semtrees = []
        for f in frames:
            tree = self.grammar.get(tree_name, copy=True)
            semtrees.append(self.add_semantics(tree, anchor, f.np_var_order, f.sem_dict))
        #semtrees = [self.add_semantics(tree_name, lemma, f.sem_dict) for f in frames]
        semtrees = [s for s in semtrees if s is not None]
        return semtrees

    def get_nonverb_tree_family(self, tree_name, anchor):
        annotations = {
            'Ts0N1': {
                'np_var_order': ['e1'],
                'sem_dict': {'Event': 'ISA(e1, %s)' % anchor.upper()},
                'event': 'e1',
            },
            'Tnx0Pnx1': {
                'np_var_order': ['a1', 'l1'],
                'sem_dict': {'Event': '%s(e1, a1, l1)' % anchor, 'a1': 'Agent(e1,a1)', 'l1': 'Location(e1, l1)'},
                'event': 'e1',
            },
            'Tnx0N1': {
                'np_var_order': ['a1'],
                'sem_dict': {'Event': 'Agent(e1,a1)', 'a1': 'ISA(a1, %s)' % anchor.upper()},
                'event': 'e1',
            },
            'Tnx0BEnx1': {
                'np_var_order': ['a1', 'l1'],
                'sem_dict': {'Event': 'Agent(e1,a1)', 'l1': '', 'a1': ''},
                'event': 'e1',
            },
            'Tnx0Ax1': {
                'np_var_order': ['a1',],
                'sem_dict': {'Event': 'Agent(e1,a1)', 'a1': 'ISA(a1, %s)' % anchor.upper()},
                'event': 'e1',
            },
            'Ts0Ax1': {
                'np_var_order': ['e1',],
                'sem_dict': {'Event': 'ISA(e1, %s)' % anchor.upper()},
                'event': 'e1',
            },
            'Ts0Pnx1': {
                'np_var_order': ['e1', 'l1'],
                'sem_dict': {'Event': '%s(e1, l1)' % anchor, 'l1': 'Theme(e1, l1)'},
                'event': 'e1',  
            },

        }

        tree = self.grammar.get(tree_name, copy=True)

        np_var_order = annotations[tree.tree_family]['np_var_order']
        sem_dict = annotations[tree.tree_family]['sem_dict']

        np_var_order = [VariableParser.parse(v)[0] for v in np_var_order]
        for v in np_var_order:
            if v.name == annotations[tree.tree_family]['event']:
                v.arg_type = 'Event'

        for var_name, sem_str in sem_dict.items():
            sem_dict[var_name] = SemanticParser.parse(sem_str)

        for v in sem_dict['Event'].variables():
            if v.name == annotations[tree.tree_family]['event']:
                v.arg_type = 'Event'

        return [self.add_semantics(tree, anchor, np_var_order, sem_dict)]

    def get_semtrees_from_pb_instance(self, tree_name, anchor, pb_instance):
        vn_classes = self.propbank.get_vn_classes(pb_instance.filenum, pb_instance.sentnum, pb_instance.word)
        frames = []
        for vn_class in vn_classes:
            frames += self.verbnet.get_frames_from_class(vn_class)

        semtrees = []
        for frame in frames:
            # Requires a new copy every time
            tree = self.grammar.get(tree_name, copy=True)

            # Skip frames from different family
            xtag_family = self.xtag_mapper.get_xtag_family(frame.primary, frame.secondary) 
            if xtag_family is None or xtag_family != tree.tree_family:
                continue

            # Return tree with semantics
            semtree = self.add_semantics(tree, anchor, frame.np_var_order, frame.sem_dict)
            semtrees.append(semtree)

        semtrees = [s for s in semtrees if s is not None]
        return semtrees

    def add_semantics(self, tree, anchor, np_var_order, sem_dict):
        """
        Given a lemma and tree names, returns sem trees given by all matching
        verb classes and their frames. This is where all of the transformation
        logic currently lives for how to compute the semantics for combinations 
        of wh/PRO/gerunds/relclauses. These essentially act as 'metagrammar rules'
        that can be applied successively.
        """

        # Currently ignore trees with more than one anchor (like Tnx0VPnx1)
        if len(tree.anchor_positions()) > 1:
            return None

        declarative_tree = self.grammar.get_declarative_tree(tree.tree_family)
        sub_nouns = [n for n in declarative_tree.subst_nodes() if n.prefix() in ["NP", "S"]]

        # Can't align semantics if wrong number of nouns/subnodes
        # Try using actual tree's subnodes (for when declarative tree is beta)
        if len(np_var_order) != len(sub_nouns):
            sub_nouns = [n for n in tree.subst_nodes() if n.prefix() in ["NP", "S"]]

        # Still can't align semantics
        if len(np_var_order) != len(sub_nouns):
            return None


        # Lexicalize tree
        tree.lexicalize(anchor)

        # Align np vars and substitution nodes
        node_entity_dict = {}
        for np_var, subst_node in zip(np_var_order, sub_nouns):
            node_entity_dict[subst_node.label()] = np_var

        tree = SemTree.convert(tree)

        # Map event semantics to root
        tree.semantics = sem_dict["Event"]

        # Replace anchor specific constants
        anchor_rename = VariableBinding({Constant("__ANCHOR__"): Constant(anchor.upper())})
        tree.semantics.apply_binding(anchor_rename)

        events = [v for v in tree.semantics.variables() if v.arg_type == "Event"]
        if len(events) == 0:
            import code; code.interact(local=locals())

        tree.sem_var = tree.semantics.event()
        # Map argument semantics to subst nodes
        for node_label, np_var in node_entity_dict.items():
            subst_node = tree.find(node_label)
            if subst_node is not None and tree.sem_var.name != np_var.name:
                #subst_node.semantics = sem_dict[np_var.name]
                tree.semantics = tree.semantics.concat(sem_dict[np_var.name])
                subst_node.sem_var = np_var
                tree.semantics.apply_binding(anchor_rename) # replace anchor specific constants

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
            nps = [n for n in tree.subtrees() if n.prefix() in ["NP", "S"] and n.label() not in ["NP_r", "NP_f", "NP_w", "S_r", "S_f", "S_w"]]
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
        tree = SemTree.convert(tree)

        '''
        if tree.initial():
            v = VariableFactory.get_var(pre=anchor[0])
        else:
            v = VariableFactory.get_var()
        '''

        sem_map = {
            "alphaNXN": {
                "NP": (lambda a: "", "x1"),
                "N": (lambda a: "ISA(x1, %s)" % a.upper(), "x1"),
            },
            "betaAn": {
                "N_r": (lambda a: "ISA(x1, %s)" % a.upper(), "x1"),
                "N_f": (lambda a: "", "x1"),
            },
            "betaNn": {
                "N_r": (lambda a: "ISA(x1, %s)" % a.upper(), "x1"),
                "N_f": (lambda a: "", "x1"),
            },
            ("betaDnx", "a"): {
                "NP_r": (lambda a: "EXISTS(x1)|", "x1"),
                "NP_f": (lambda a: "", "x1"),
            },
            ("betaDnx", "an"): {
                "NP_r": (lambda a: "EXISTS(x1)|", "x1"),
                "NP_f": (lambda a: "", "x1"),
            },
            ("betaDnx", "the"): {
                "NP_r": (lambda a: "EXISTS(x1)|", "x1"),
                "NP_f": (lambda a: "", "x1"),
            },
            ("betaDnx", "one"): {
                "NP_r": (lambda a: "EXISTS(x1)|", "x1"),
                "NP_f": (lambda a: "", "x1"),
            },
            "betaVvx": {
                "VP_r": (lambda a: "", "x1"),
                "VP": (lambda a: "", "x1"),
            },
            "betanxPnx": {
                "NP_r": (lambda a: "%s(x1, y1)" % a, "x1"),
                "NP": (lambda a: "", "y1"),
                "NP_f": (lambda a: "", "x1"),
            },
            "betavxPnx": {
                "VP_r": (lambda a: "%s(x1, y1)" % a, "x1"),
                "NP": (lambda a: "", "y1"),
                "VP": (lambda a: "", "x1"),
            },
            "betasPUs": {
                "S_r": (lambda a: "", "AND(x1,y1)"),
                "S_f": (lambda a: "", "x1"),
                "S_1": (lambda a: "", "y1"),
            },
            "betaARBvx": {
                "VP": (lambda a: "", "x1"),
                "VP_r": (lambda a: "%s(x1)" % a, "x1"),
            },
            "betanxPUnx": {
                "NP_f": (lambda a: "", "x1"),
                "NP_r": (lambda a: "equal(x1,y1)", "x1"),
                "NP": (lambda a: "", "y1"),
            },
            "betaPUs": {
                "S_r": (lambda a: "", "x1"),
                "S": (lambda a: "", "x1"),
            },
            "betaVs": {
                "S_r": (lambda a: "", "x1"),
                "S": (lambda a: "", "x1"),
            },
            "betanx1CONJnx2": {
                "NP": (lambda a: "", "AND(x1,y1)"),
                "NP_1": (lambda a: "", "x1"),
                "NP_2": (lambda a: "", "y1"),
            },
            "betanxGnx": {
                "NP_r": (lambda a: "EXISTS(x1)|belongs_to(x1,y1)", "x1"),
                "NP_f": (lambda a: "", "x1"),
                "NP": (lambda a: "", "y1"),
            },
            "betavxPs": {
                "VP_r": (lambda a: "", "x1"),
                "VP_f": (lambda a: "", "x1"),
                "PP": (lambda a: "%s(x1, y1)" % a, "y1"),
                "S": (lambda a: "", "y1"),
            },
            "betas1CONJs2": {
                "S": (lambda a: "", "AND(x1,y1)"),
                "S_1": (lambda a: "", "x1"),
                "S_2": (lambda a: "", "y1"),
            },
            "betaARBs": {
                "S": (lambda a: "", "x1"),
                "S_r": (lambda a: "%s(x1)" % a, "x1"),
            },
            "betaCONJs": {
                "S_c": (lambda a: "", "x1"),
                "S_r": (lambda a: "", "x1"),
            },
        }


        if (tree_name, anchor) in sem_map:
            key = (tree_name, anchor)
        elif tree_name in sem_map:
            key = tree_name
        else:
            #print(tree_name, anchor)
            raise NotImplementedError

        node_dict = sem_map[key]
        for node_label, (sem_str, var_str) in node_dict.items():
            sem_str = sem_str(anchor)
            node = tree.find(node_label)
            node.semantics = SemanticParser.parse(sem_str)
            var, rest = VariableParser.parse(var_str)
            node.sem_var = var

        return tree

if __name__ == '__main__':
    g = Grammar.load()
    vnet = VerbNet.load()
    mapper = XTAGMapper.load()
    propbank = Propbank.load()
    s = SemTreeGrammar(g, vnet, mapper, propbank)

    jump = s.get_semtree('alphanx0Vnx1', 'jumped', lemma='run')
    tree_families = set(mapper.xtag_mapping.values())
    all_trees = set()
    for tf in tree_families:
        all_trees.update([t.tree_name for t in g.get_trees_from_tree_family(tf)])
        print(tf)
    #for tree_name in sorted(all_trees):
    #    print(tree_name)
    '''

    '''
    chase_ps = s.get_semtree('alphanx0Vnx1', 'chase', lemma='run')
    cat_ps = s.get_semtree('alphaNXN', 'cat')
    dog_ps = s.get_semtree('alphaNXN', 'dog')
    red_ps = s.get_semtree('betaAn', 'red')
    the_ps = s.get_semtree('betaDnx', 'a')
    chase_ps = chase_ps.substitute(cat_ps, 'NP_0')
    chase_ps = chase_ps.substitute(dog_ps, 'NP_1')
    chase_ps = chase_ps.adjoin(red_ps, "N")
    chase_ps = chase_ps.adjoin(the_ps, 'NP_0')
    #for sub in chase_ps.subtrees():
    #    print(sub.label(), sub.semantics)
    chase_ps.draw()

    '''
    results = []
    success, missing, index, key = 0, 0, 0, 0
    deriv_trees = DerivationTree.load_all(treedir=DATA_DIR + 'revised_parse_trees')
    for deriv in deriv_trees:
        try:
            parse = deriv.get_parse_tree(s)
            success += 1
        except NotImplementedError:
            missing += 1
            continue
        except IndexError:
            index += 1
            continue
        except KeyError:
            key += 1
            continue

        sem = parse.full_semantics()
        result = {"sentence": "%s_%s.parse" % (deriv.file_num, deriv.sentence_num), "semantics": str(sem)}
        results.append(result)
        print(result)

    print("success %d, missing %d, index %d, key %d, total %d" % (success, missing, index, key, len(deriv_trees)))
    with open("data/semantics.json", "w") as f:
        json.dump(results, f, indent=1)
    '''
