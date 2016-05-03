import nltk, copy

from collections import defaultdict
from nltk.featstruct import FeatStruct

from semantics import Semantics, Variable

class TAGTree(nltk.ParentedTree):
    """
    Class representing a tree (either initial or auxiliary) in the XTAG grammar
    Label specified as "prefix_suffix-renamesuffix", i.e. "NP_0-1"
    """
    def __init__(self, label, tree_name=None, tree_family=None, fs=None, children=None):
        if children is None:
            children = []
        self._label = label
        self.tree_name = tree_name
        self.tree_family = tree_family
        self.subst = False
        self.anchor = False
        self.lex = False
        self.foot = False
        self.can_adjoin = True
        self.must_adjoin = False
        self.deriv_depth = None # Useful for composing derivation tree
        if fs is None:
            fs = FeatStruct() 
        self.fs = fs
        nltk.ParentedTree.__init__(self, self._label, children)

    def is_root(self):
        return self.parent() is None

    def initial(self):
        """Returns True if an initial tree"""
        return "alpha" in self.tree_name

    def leaves(self):
        return [s.label() for s in self.subtrees() if len(s) == 0]

    def anchors(self):
        return list(self.subtrees(lambda t: t.lex))

    def auxiliary(self):
        """Returns True if an auxiliary tree"""
        return "beta" in self.tree_name

    def belongs_to_verb_family(self):
        """Returns True if this tree belongs to a verb family"""
        return self.tree_family[0] == "T"

    def anchor_positions(self):
        """Returns nodes where lexicalization can occur"""
        return list(self.subtrees(lambda t: t.anchor))

    def subst_nodes(self):
        """Returns nodes which are open for substitution"""
        return list(self.subtrees(lambda t: t.subst))

    def find(self, label):
        """Returns the node whose label matches label"""
        for s in self.subtrees():
            if s.label() == label:
                return s

    def foot_node(self):
        """Returns the foot node of an auxiliary tree"""
        for s in self.subtrees():
            if s.foot:
                return s

    def prefix(self):
        """Returns the prefix of the node label (everything before '_')"""
        return self.label().split("_")[0].split("-")[0]

    def original_label(self):
        """Returns the label before any renames occurred (everything before "-")"""
        return self.label().split("-")[0]

    def suffix(self):
        """
        Returns the suffix of the node label (everything after "_" and before renaming)
        i.e. "0" in "NP_0-1"
        """
        return self.label().split("_")[1].split("-")[0]

    def rename_suffix(self):
        """
        Returns the rename suffix that has been added to force label uniqueness
        (everything after '-'). i.e. "1" in "NP_0-1"
        """
        return self.label().split("_")[1].split("-")[1]

    def has_control(self):
        """
        Returns True if feature structure has a 'control' attribute. This is
        used for PRO constructions (to specify which noun was replaced)
        """
        for fs in self.fs.walk():
            if 'control' in fs:
                return True
        return False

    def has_trace(self):
        """
        Returns True if feature structure has a 'trace' attribute. This is used
        for relative clauses (to specify which noun phrase was extracted)
        """
        for fs in self.fs.walk():
            if 'trace' in fs:
                return True
        return False

    def has_pro(self):
        """Returns True if any node in tree has PRO label"""
        return any([c.label() == "PRO" for c in self])

    def lexicalize(self, anchors):
        """
        Lexicalizes tree, given a list of anchors. Raises an exception if the
        number of anchors and anchor positions is not the same
        """
        if not isinstance(anchors, list):
            anchors = [anchors] 

        assert len(self.anchor_positions()) == len(anchors)
        for anchor_parent, anchor in zip(self.anchor_positions(), anchors):
            anchor_node = TAGTree(anchor)
            anchor_node.lex = True
            anchor_parent.append(anchor_node)
        return self

    def label_counts(self):
        """
        Returns a dictionary mapping node_label -> number of times used in 
        tree. i.e. {NP_0: 2, S: 1, ...}
        """
        counts = defaultdict(int)
        for s in self.subtrees():
            counts[s.original_label()] += 1
        return counts

    def rename(self, label_counts):
        """
        Given a dictionary of label counts, renames the nodes in this tree to
        avoid conflicts. Typically, the dictionary of label counts would come
        from the base tree that this tree is being substituted/adjoined into
        """
        rename_dict = {}
        for s in self.subtrees(lambda s: not s.lex):
            if s.original_label() in label_counts:
                new_label = "%s-%d" % (s.original_label(), label_counts[s.original_label()])
                label_counts[s.original_label()] += 1
                rename_dict[s.label()] = new_label
                s._label = new_label
        return rename_dict

    def substitute(self, t2, label):
        """Returns this node after substituting the tree t2 at this location"""
        node = self.find(label)
        t2 = t2.copy()
        t2.rename(self.label_counts())
        assert node.subst
        assert node.prefix() == t2.prefix()
        for c in t2:
            node.append(c)
        node.subst = False
        return self

    def adjoin(self, t2, label):
        """Returns this node after adjoining the tree t2 at this location"""
        adj_node = self.find(label)
        t2 = t2.copy()
        t2.rename(self.label_counts())
        assert not adj_node.subst and not adj_node.lex
        if adj_node.prefix() != t2.prefix():
            print(adj_node.label(), t2.label())
            print(self.tree_name)
            print(t2.tree_name)

        assert adj_node.prefix() == t2.prefix()
        foot = t2.foot_node()

        if foot is None:
            print(self.tree_name)
            print(t2.tree_name)
            self.draw()
            t2.draw()
        assert foot is not None

        # Move children of adjunction node to foot node
        for c in adj_node:
            foot.append(c) 

        # Replace original children with new node + foot node
        while len(adj_node) > 0:
            adj_node.pop()
        assert len(adj_node) == 0

        for c in t2:
            adj_node.append(c)

        foot.foot = False
        return self

    def copy(self):
        """Returns a deep copy of this tree"""
        new_tree = TAGTree(self.label(), children=[c.copy() for c in self])
        new_tree.tree_name = self.tree_name
        new_tree.tree_family = self.tree_family
        new_tree.subst = self.subst
        new_tree.anchor = self.anchor
        new_tree.lex = self.lex
        new_tree.foot = self.foot
        new_tree.can_adjoin = self.can_adjoin
        new_tree.must_adjoin = self.must_adjoin
        new_tree.deriv_depth = self.deriv_depth
        new_tree.fs = self.fs
        return new_tree

    def _setparent(self, child, index, dry_run=False):
        """
        Override parent management so that we don't care if a child has an 
        existing parent during parent assignment
        """
        # If the child's type is incorrect, then complain.
        if not isinstance(child, nltk.ParentedTree):
            raise TypeError('Can not insert a non-ParentedTree '+
                            'into a ParentedTree')
        # Set child's parent pointer & index.
        if not dry_run:
            child._parent = self

    def _delparent(self, child, index):
        """
        Changing setparent behavior can cause sanity checks to fail, so
        override those too
        """
        assert isinstance(child, nltk.ParentedTree)
        child._parent = None

    @classmethod
    def convert(cls, val):
        """Returns an nltk.Tree converted to a TAGTree"""
        if isinstance(val, nltk.Tree):
            children = [cls.convert(child) for child in val]
            return cls(val._label, children=children)
        else:
            return val

    @classmethod
    def parse_featstruct(cls, fs_dict):
        """Returns an nltk.FeatStruct parsed from the XTAG XML"""
        fs = FeatStruct()
        if 'f' not in fs_dict:
            return fs

        # Because of xml -> dict parsing, single element doesn't look like list
        if not isinstance(fs_dict['f'], list):
            fs_dict['f'] = [fs_dict['f']]

        for f in fs_dict['f']:
            name = f['@name']
            if 'fs' in f:
                fs[name] = cls.parse_featstruct(f['fs'])
            elif 'sym' in f:
                if '@value' in f['sym']:
                    fs[name] = f['sym']['@value']
                elif '@varname' in f['sym']:
                    fs[name] = nltk.sem.logic.Variable(f['sym']['@varname'])
        return fs

    @classmethod
    def from_node_dict(cls, d, tree_name, tree_family):
        """
        Returns a TAGTree from the node dict representation (result of 
        converting XML to dictionary using xmltodict)
        """

        name = d['@name']
        subst = False
        anchor = False
        foot = False
        if d['@type'] == 'subst':
            subst = True
        elif d['@type'] == 'anchor':
            anchor = True
        elif d['@type'] == 'foot':
            foot = True

        narg = d['narg']
        fs = narg['fs']
        fs = cls.parse_featstruct(fs)

        children = []
        if 'node' in d:
            nodes = d['node']
            if isinstance(nodes, dict):
                nodes = [nodes]
            children = [TAGTree.from_node_dict(n, tree_name=tree_name, tree_family=tree_family) for n in nodes]
        tree = TAGTree(name, tree_name=tree_name, tree_family=tree_family, fs=fs, children=children)
        tree.subst = subst
        tree.anchor = anchor
        tree.foot = foot
        return tree

    @classmethod
    def from_dict(cls, d):
        """
        Returns TAGTree from parent of node dict. Necessary because that is 
        where tree name and family information is stored (has to be passed to
        every node in tree
        """
        tree_family = d['family']
        tree = d['tree']
        tree_name = tree['@id']
        # Necessary b/c OS X cannot handle filenames that are same but case is different
        tree_name = tree_name.replace("nx0V_pnx1", "nx0Vpnx1").replace("nx0Vnx1_pnx2", "nx0Vnx1pnx2")
        tree_family = tree_family.replace("nx0V_pnx1", "nx0Vpnx1").replace("nx0Vnx1_pnx2", "nx0Vnx1pnx2")
        return TAGTree.from_node_dict(tree['node'], tree_name, tree_family)

class SemTree(TAGTree):
    def __init__(self, label, tree_name=None, tree_family=None, fs=None, children=None,
        semantics=None, sem_var=None, sem_var_quant=None):
        if semantics is None:
            semantics = Semantics([])
        self._label = label
        self.semantics = semantics
        self.sem_var = sem_var
        self.sem_var_quant = sem_var_quant
        TAGTree.__init__(self, self._label, tree_name=tree_name, tree_family=tree_family, children=children, fs=fs)

    def variable(self):
        node = self
        while node is not None:
            if node.sem_var is not None:
                return node.sem_var
            node = node.parent()

    def sem_suffixes_used(self):
        all_suffixes = defaultdict(set)
        for s in self.subtrees():
            suffixes = s.semantics.suffixes_used()
            for prefix, suffix_list in suffixes.items():
                all_suffixes[prefix].update(suffix_list)
        return all_suffixes

    def apply_semantic_binding(self, binding):
        self.semantics.apply_binding(binding)
        if self.sem_var in binding:
            self.sem_var = binding[self.sem_var]
        return self

    def substitute(self, tree2, label):
        tree2 = tree2.copy()
        tree2.rename(self)

        ### Syntax ###
        sub_node = self.find(label)
        assert sub_node.subst
        assert sub_node.prefix() == tree2.prefix()
        for c in tree2:
            sub_node.append(c)
        sub_node.subst = False

        ### Semantics ###
        rename_dict = {sub_node.variable().name: tree2.variable().name}
        sub_node.semantics = sub_node.semantics.concat(tree2.semantics)
        while sub_node is not None:
            sub_node.apply_semantic_binding(rename_dict)
            sub_node = sub_node.parent()

        return self

    def adjoin(self, tree2, label):
        tree2 = tree2.copy()
        tree2.foot_node()._label = label # Force foot to lose the _f name scheme
        tree2.rename(self) 

        ### Syntax ###
        adj_node = self.find(label)
        foot = tree2.foot_node()
        assert adj_node is not None
        assert not adj_node.subst and not adj_node.lex
        assert adj_node.prefix() == tree2.prefix()
        assert foot is not None

        # Move children of adjunction node to foot node
        for c in adj_node:
            foot.append(c) 

        # Replace original children with new node + foot node
        while len(adj_node) > 0:
            adj_node.pop()
        assert len(adj_node) == 0

        for c in tree2:
            adj_node.append(c)
        foot.foot = False

        ### Semantics ###
        rename_dict = {tree2.variable().name: adj_node.variable().name}
        for s in tree2.subtrees():
            s.apply_semantic_binding(rename_dict)
        adj_node.semantics = adj_node.semantics.concat(tree2.semantics)

        # Quantifiers 
        if tree2.sem_var_quant is not None:
            node = adj_node
            while node.sem_var is not None:
                node = node.parent()
            node.sem_var_quant = tree2.sem_var_quant
            node.semantics.set_quantification(tree2.sem_var_quant)

        return self


    def rename(self, tree1):
        """
        Returns self after performing tree and sem renames to prevent conflicts
        with given semtree (tree1). tree1 is typically a tree that self will
        be applied to (via substitution or adjunction)
        """               
        label_counts = tree1.label_counts()
        sem_rename_dict = {}
        suffixes_used = tree1.sem_suffixes_used()

        for s in self.subtrees(lambda s: not s.lex):
            ### Update tree labels ###
            if s.original_label() in label_counts:
                new_label = "%s-%d" % (s.original_label(), label_counts[s.original_label()])
                label_counts[s.original_label()] += 1
                s._label = new_label

            ### Update Semantics ###
            additional_renames = s.semantics.get_rename_dict(suffixes_used)

            # Need to update suffixes used when we add a new one
            for old, new in additional_renames.items():
                if old not in sem_rename_dict:
                    new = Variable(new)
                    sem_rename_dict[old] = new.name
                    suffixes_used[new.prefix()].add(new.suffix())

            # update semantics
            s.apply_semantic_binding(sem_rename_dict)
        return self

    def copy(self):
        new_tree = SemTree(self.label(), children=[c.copy() for c in self])
        new_tree.tree_name = self.tree_name
        new_tree.tree_family = self.tree_family
        new_tree.subst = self.subst
        new_tree.anchor = self.anchor
        new_tree.lex = self.lex
        new_tree.foot = self.foot
        new_tree.can_adjoin = self.can_adjoin
        new_tree.must_adjoin = self.must_adjoin
        new_tree.deriv_depth = self.deriv_depth
        new_tree.fs = self.fs
        new_tree.semantics = self.semantics
        new_tree.sem_var = self.sem_var
        new_tree.sem_var_quant = self.sem_var_quant
        return new_tree

    @classmethod
    def convert(cls, val):
        """Returns an nltk.Tree converted to a TAGTree"""
        if isinstance(val, nltk.Tree):
            children = [cls.convert(child) for child in val]
            new_tree = cls(val._label, tree_name=val.tree_name, 
                       tree_family=val.tree_family, fs=val.fs, 
                       children=children, semantics=Semantics([]),
                       sem_var=None, sem_var_quant=None)

            new_tree.subst = val.subst
            new_tree.anchor = val.anchor
            new_tree.lex = val.lex
            new_tree.foot = val.foot
            new_tree.can_adjoin = val.can_adjoin
            new_tree.must_adjoin = val.must_adjoin
            new_tree.deriv_depth = val.deriv_depth
            return new_tree
        else:
            return val
