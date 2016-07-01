import os, pickle, re

from collections import defaultdict
from nltk.corpus.reader.verbnet import VerbnetCorpusReader

from vnet_constants import DATA_DIR
from semantics import Semantics, VariableFactory

class VerbNet(object):
    """
    Class storing the full set of VerbNet Frames. Provides an interface to get
    all of the frames associated with a given lemma
    """

    def __init__(self, lemma_to_classes, class_to_frames, frame_dict, class_id_dict):
        self.lemma_to_classes = lemma_to_classes # {chase -> [chase-51.6]}
        self.class_to_frames = class_to_frames # {chase-51.6 -> [chase, follow, pursue, ...]}
        self.class_id_dict = class_id_dict # {51.6 -> chase-51.6}

    def get_frames_from_class(self, class_id):
        if class_id in self.class_id_dict:
            class_id = self.class_id_dict[class_id]
        if class_id == '-':
            return []

        return self.class_to_frames[class_id]

    def get_frames(self, lemma, class_id=None):
        """Returns all frames associated with a lemma. Filters by class id if provided"""
        assert lemma in self.lemma_to_classes
        classes = self.lemma_to_classes[lemma]
        if class_id is not None:
            classes = [cid for cid in classes if cid == class_id]

        frames = []
        for cid in classes:
            frames += self.class_to_frames[cid]

        return frames

    @classmethod
    def fromxml(cls, dirname=DATA_DIR + 'verbnet'):
        """
        Returns VerbNet object after parsing the full VerbNet corpus from directory
        of XML files
        """

        class_to_frames = {}
        lemma_to_classes = defaultdict(list)
        frame_dict = {}
        class_id_dict = {}

        vnet = VerbnetCorpusReader(dirname, r'.*.xml')
        for vn_class in vnet.classids():
            frames = []

            try:
                frame_xmls = vnet.vnclass(vn_class).find("FRAMES")
            except AssertionError:
                continue

            for i, frame_xml in enumerate(frame_xmls):
                try:
                    frame = Frame.fromxml(vn_class, frame_xml, i)
                    frames.append(frame)
                except AttributeError:
                    # This is (apparently) a rare bug in nltk's loader
                    # Only happens with "slide"
                    continue

                # Reset after parsing a frame so that we don't have huge numbers
                VariableFactory.count_dict = defaultdict(int)

            # Store shorted vn_class b/c that's what propbank references
            shortened_vn_class = re.search(r"-([\d|\.|-]+)", vn_class).group(1)
            class_id_dict[shortened_vn_class] = vn_class

            class_to_frames[vn_class] = frames
            lemmas = vnet.lemmas(vn_class)
            for lemma in lemmas:
                lemma_to_classes[lemma].append(vn_class)

        return VerbNet(lemma_to_classes, class_to_frames, frame_dict, class_id_dict)

    @classmethod
    def load(cls, xml_dirname=DATA_DIR + 'verbnet'):
        pickle_filename = DATA_DIR + 'verbnet.pickle'
        if os.path.exists(pickle_filename):
            return pickle.load(open(pickle_filename, 'rb'))
        else:
            verbnet = cls.fromxml(xml_dirname)
            pickle.dump(verbnet, open(pickle_filename, 'wb'))
            return verbnet

class Frame(object):
    """Class representing a single verb frame in VerbNet"""
    def __init__(self, vn_class, frame_num, primary, secondary, sem_dict, np_var_order, example):
        self.vn_class = vn_class
        self.vn_class_id = vn_class.split("-")[-1]
        self.frame_num = frame_num
        self.primary = primary
        self.secondary = secondary
        self.sem_dict = sem_dict
        self.np_var_order = np_var_order
        self.example = example
        self.lemma = None

    def lexicalize(self, lemma):
        """Returns self after adding any semantics that are specific to the lemma"""
        self.lemma = lemma
        titleized = lemma[0].upper() + lemma[1:]
        self.sem_dict["Event"].apply_binding({'__ANCHOR__': titleized})
        return self

    @classmethod
    def fromxml(cls, vn_class, xml, frame_num):
        """Returns a Frame object from the VerbNet XML representation"""
        primary = xml.find("DESCRIPTION").attrib.get("primary", "")
        secondary = xml.find("DESCRIPTION").attrib.get("secondary", "")
        sem_dict = Semantics.semdict_fromxml(xml.find("SEMANTICS"))

        # Need the order of np vars given in syntax for mapping to subst nodes
        nps = xml.find("SYNTAX").findall("NP")
        np_order = [np.attrib["value"] for np in nps]
        sem_vars = [v for s in sem_dict.values() for v in s.variables()]
        np_var_order = []
        for np in np_order:
            match = [v for v in sem_vars if v.orig_name == np]
            if len(match) > 0 and not match[0].missing: # Ignore "?" variables
                np_var_order.append(match[0])

        example = xml.find("EXAMPLES").find("EXAMPLE").text.replace('"', '')
        return Frame(vn_class, frame_num, primary, secondary, sem_dict, np_var_order, example)

class XTAGMapper(object):
    """
    Class providing the mapping from a VerbNet frame to an XTAG tree. While this
    research was discussed in an ACL paper, the authors never responded to my 
    requests for the mapping, so the file we are using comes from some FTP server
    that was hosting old stanford parser files.
    """
    def __init__(self, xtag_mapping):
        self.xtag_mapping = xtag_mapping

    def get_xtag_family(self, primary, secondary):
        """Given the primary and secondary fields of a frame, returns xtag family"""
        return self.xtag_mapping.get((primary, secondary))

    @classmethod
    def load(cls, filename=DATA_DIR + 'verbnet_xtag_mapping.txt'):
        """Returns XTAGMapper from the txt file containing logic"""
        with open(filename, 'r') as f:
            mapping_contents = f.readlines() 

        xtag_mapping = {}
        for line in mapping_contents:
            if "primary" in line:
                vnet_dict = cls.parseline(line.strip())
                xtag_mapping[(vnet_dict["primary"], vnet_dict["secondary"])] = vnet_dict["xtag"]
        return XTAGMapper(xtag_mapping)

    @classmethod
    def parseline(cls, line):
        """Parse logic to turn individual line into verbnet-xtag mapping"""
        primary = re.search("primary=\"(.*?)\"", line).group(1)
        secondary = re.search("secondary=\"(.*?)\"", line).group(1)
        xtag = re.search("xtag=\"(.*?)\"", line).group(1)

        name = re.search("name=\"(.*?)\"", line).group(1)
        return {
            'primary': primary,
            'secondary': secondary,
            'name': name,
            'xtag': xtag
        }
