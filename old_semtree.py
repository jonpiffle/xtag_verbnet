import copy

class SemTree(object):
    """
    Class representing a semantically-annotated LTAG tree. This is really a single
    mapping of a TAGTree and a Semantics object (associated with a VerbNet frame)
    """
    def __init__(self, tree, sem, node_entity_dict=None, frame=None):
        self.tree = tree # TAGTree
        self.sem = sem # Semantics
        self.frame = frame # Frame that semantics came from

        # Maps each tree node to sem entity
        if node_entity_dict is None:
            node_entity_dict = {}
        self.node_entity_dict = node_entity_dict

    def get_entity(self, label):
        """Returns the semantics entity associated with the given node label"""
        return self.node_entity_dict.get(label)

    def rename(self, semtree1):
        """
        Returns self after performing tree and sem renames to prevent conflicts
        with given semtree (semtree1). semtree1 is typically tree that self will
        be applied to (via substitution or adjunction
        """               
        # Update tree
        label_counts = semtree1.tree.label_counts()
        syn_rename_dict = self.tree.rename(label_counts)

        # Update node_entity_dict after rename
        for old_label, new_label in syn_rename_dict.items():
            if old_label in self.node_entity_dict:
                self.node_entity_dict[new_label] = self.node_entity_dict.pop(old_label)

        # Update Semantics
        suffixes_used = semtree1.sem.suffixes_used()
        sem_rename_dict = self.sem.get_rename_dict(suffixes_used)
        self.sem.apply_binding(sem_rename_dict)

        # Update node_entity_dict after rename
        for entity in self.node_entity_dict.values():
            entity.apply_binding(sem_rename_dict)

        return self

    def substitute(self, semtree2, label):
        """
        Performs LTAG substitution of semtree2.tree into self.tree at label. 
        Then updates semantics to reflect the semantic effect of substitution.
        This means that any 'free' variables at the substitution site will
        be bound to the variables introduced by semtree2 via renaming
        """
        # Copy and Rename
        semtree2 = semtree2.copy()
        semtree2.rename(self)

        # Syntax
        sub_node = self.tree.find(label)
        assert sub_node is not None
        sub_node.substitute(semtree2.tree)

        # Semantics
        sub_node_entity = self.get_entity(sub_node.label())
        semtree2_entity = semtree2.get_entity(semtree2.tree.label())
        rename_dict = {sub_node_entity.name: semtree2_entity.name}
        self.sem.apply_binding(rename_dict)

        self.sem = self.sem.concat(semtree2.sem)
        self.node_entity_dict[sub_node.label()] = semtree2_entity
        del semtree2.node_entity_dict[semtree2.tree.label()]

        self.node_entity_dict.update(semtree2.node_entity_dict)
        return self

    def adjoin(self, semtree2, label):
        """
        Performs LTAG adjunction of semtree2.tree on self.tree at label. 
        Then updates semantics to reflect the semantic effect of adjunction.
        This means that any 'free' variables in the adjunction tree will
        be bound to the variables in self via renaming
        """
        # Copy and Rename
        semtree2 = semtree2.copy()
        semtree2.tree.foot_node()._label = label # Force foot to lose the _f name scheme
        semtree2.rename(self)

        # Syntactic
        adj_node = self.tree.find(label)
        assert adj_node is not None
        adj_node.adjoin(semtree2.tree)

        # Semantic
        adj_node_entity = self.get_entity(adj_node.label())
        semtree2_entity = semtree2.get_entity(semtree2.tree.label())
        for label, entity in semtree2.node_entity_dict.items():
            if entity == semtree2_entity:
                self.node_entity_dict[label] = adj_node_entity
            else:
                self.node_entity_dict[label] = entity
        rename_dict = {semtree2_entity.name: adj_node_entity.name}
        semtree2.sem.apply_binding(rename_dict)
        self.sem = self.sem.concat(semtree2.sem)
        return self

    def copy(self):
        """Returns a deepcopy of self"""
        new_semtree = SemTree(
            self.tree.copy(),
            copy.deepcopy(self.sem),
            copy.deepcopy(self.node_entity_dict),
            copy.deepcopy(self.frame)
        )
        return new_semtree

    def __str__(self):
        return "%s\n%s" % (str(self.tree), str(self.sem))

    def __repr__(self):
        return str(self)
