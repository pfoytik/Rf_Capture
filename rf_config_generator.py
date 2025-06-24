from PyQt5 import Qt
import sys
import json

class App(Qt.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RF Config Generator")

        toolBar = Qt.QToolBar()
        pushButton = Qt.QPushButton("Open...")
        pushButton.clicked.connect(self.open_config)
        toolBar.addWidget(pushButton)
        pushButton = Qt.QPushButton("New")
        pushButton.clicked.connect(self.new_config)
        toolBar.addWidget(pushButton)
        pushButton = Qt.QPushButton("Save Config...")
        pushButton.clicked.connect(self.save_config)
        toolBar.addWidget(pushButton)
        self.addToolBar(toolBar)

        self.setGeometry(200,200,800,600)

    def generateLayout(self):
        mainLayout = Qt.QVBoxLayout()
        mainLayout.setSizeConstraint(Qt.QLayout.SizeConstraint.SetMinimumSize)
        mainLayout.setGeometry(Qt.QRect(0,0,800,600))
        return mainLayout

    def open_config(self):


        fileDialog = Qt.QFileDialog(self)
        fileDialog.setWindowTitle("Open Existing Config File")
        fileDialog.setFileMode(Qt.QFileDialog.FileMode.ExistingFile)
        fileDialog.setViewMode(Qt.QFileDialog.ViewMode.Detail)
        fileDialog.setNameFilter('*.json')

        if not fileDialog.exec():
            return
        selected_conf = fileDialog.selectedFiles()[0]
        with open(selected_conf) as f:
            config = json.load(f)



        self.freq_config = FrequencyConfig()
        self.capture_settings = CaptureSettings(config["capture_settings"])
        self.scheduling = SchedulingSlots(config["scheduling"]["time_slots"])

        collection_modes = []
        for k,v in config["collection_modes"].items():
            new_dict = config["collection_modes"][k]
            new_dict["name"] = k
            collection_modes.append(new_dict)

        self.collection_modes = CollectionModes(collection_modes)

        for name,entries in config["frequencies"].items():
           self.freq_config.add_group(name,entries)

        self.mainLayout = self.generateLayout()

        self.mainLayout.addWidget(self.freq_config)
        self.mainLayout.addWidget(self.capture_settings)
        secondLayout = Qt.QHBoxLayout()
        secondLayout.addWidget(self.collection_modes)
        secondLayout.addWidget(self.scheduling)
        self.mainLayout.addLayout(secondLayout)

        self.centralWidget = Qt.QWidget()
        self.centralWidget.setLayout(self.mainLayout)

        self.scroll = Qt.QScrollArea()
        self.scroll.setGeometry(Qt.QRect(0,0,800,600))
        self.scroll.setWidget(self.centralWidget)

        self.setCentralWidget(self.scroll)

    def new_config(self):
        self.freq_config = FrequencyConfig()
        self.capture_settings = CaptureSettings()
        self.collection_modes = CollectionModes()
        self.scheduling = SchedulingSlots()

        self.mainLayout = self.generateLayout()
        self.mainLayout.addWidget(self.freq_config)
        self.mainLayout.addWidget(self.capture_settings)
        secondLayout = Qt.QHBoxLayout()
        secondLayout.addWidget(self.collection_modes)
        secondLayout.addWidget(self.scheduling)
        self.mainLayout.addLayout(secondLayout)

        self.centralWidget = Qt.QWidget()
        self.centralWidget.setLayout(self.mainLayout)

        self.scroll = Qt.QScrollArea()
        self.scroll.setGeometry(Qt.QRect(0,0,800,600))
        self.scroll.setWidget(self.centralWidget)

        self.setCentralWidget(self.scroll)

    def save_config(self):
        fileDialog = Qt.QFileDialog(self)
        fileDialog.setWindowTitle("Save Config File")
        fileDialog.setFileMode(Qt.QFileDialog.FileMode.AnyFile)
        fileDialog.setAcceptMode(Qt.QFileDialog.AcceptMode.AcceptSave)
        fileDialog.setViewMode(Qt.QFileDialog.ViewMode.Detail)
        fileDialog.setNameFilter('*.json')

        if not fileDialog.exec():
            return
         
        selected_conf = fileDialog.selectedFiles()[0]

        to_save = {}
        to_save["frequencies"] = self.freq_config.to_dict()
        to_save["capture_settings"] = self.capture_settings.to_dict()
        to_save["collection_modes"] = self.collection_modes.to_dict()
        to_save["scheduling"] = self.scheduling.to_dict()

        # print(f'{to_save}')

        with open(selected_conf, "w") as f:
            json.dump(to_save, f, indent=2)
    
class FrequencyConfig(Qt.QWidget):
    def __init__(self, fn=None):
        super().__init__()
        if fn is not None:
            populate(fn)
        self.layout = Qt.QHBoxLayout()
        pushButton = Qt.QPushButton("New Frequency Group")
        pushButton.clicked.connect(self.add_group_signal)
        self.layout.addWidget(pushButton)
        self.setLayout(self.layout)
        self.groups = []

    def populate(self, fn):
        pass

    def add_group_signal(self):
        self.add_group()

    def add_group(self, name=None, args=None):
        self.groups.append(FrequencyGroup(name, args))
        self.layout.addWidget(self.groups[-1])

    def to_dict(self):
        return {w.get_name(): w.to_dict() for w in self.groups}


class FrequencyGroup(Qt.QWidget):
    def __init__(self, name=None, entries=None):
        super().__init__()
        self.layout = Qt.QVBoxLayout()
        self.widgets = list()
        pushButton = Qt.QPushButton("New Entry")
        pushButton.clicked.connect(self.add_entry)
        self.group_name = Qt.QLineEdit()
        self.group_name.setPlaceholderText('group_name')
        self.layout.addWidget(pushButton)
        self.layout.addWidget(self.group_name)
        self.setLayout(self.layout)
        if entries is not None:
            self.group_name.setText(name)
            for entry in entries:
                # print(f'Appending entry {entry}')
                freqEntry = DictEntry(entry)
                self.widgets.append(freqEntry)
                self.layout.addWidget(self.widgets[-1])
            return

    def add_entry(self):
        #self.widgets.append(FrequencyEntry())
        freqEntry = DictEntry()
        freqEntry.add_entry("name", placeholder="bandwidth_name")
        freqEntry.add_entry("freq", placeholder="center_frequency")
        freqEntry.add_entry("description", placeholder="description of channel")
        self.widgets.append(freqEntry)
        self.layout.addWidget(self.widgets[-1])

    def to_dict(self):
        return [x.to_dict() for x in self.widgets]

    def get_name(self):
        return self.group_name.displayText()

class CaptureSettings(Qt.QWidget):
    def __init__(self, args=None):
        super().__init__()
        self.layout = Qt.QHBoxLayout()
        compression_widget = Qt.QComboBox()
        compression_widget.addItem("zstd")
        compression_level_widget = Qt.QComboBox()
        for i in range(1,23):
            compression_level_widget.addItem(str(i))
        if args is not None:
            compression_level_widget.setCurrentIndex(args["compression_level"])
            self.widgets = {
                    "sample_rates": TitledListWidget("Sample Rates", args["sample_rates"], float),
                    "durations": TitledListWidget("Durations", args["durations"], float),
                    "gains": TitledListWidget("Gains", args["gains"], float),
                    "compression": compression_widget,
                    "compression_level": compression_level_widget,
            }
        else:
            self.widgets = {
                    "sample_rates": TitledListWidget("Sample Rates"),
                    "durations": TitledListWidget("Durations"),
                    "gains": TitledListWidget("Gains"),
                    "compression": compression_widget,
                    "compression_level": compression_level_widget,
            }

        for v in self.widgets.values():
            self.layout.addWidget(v)
        self.setLayout(self.layout)

    def to_dict(self):
        ret = {}
        ret["sample_rates"] = self.widgets["sample_rates"].to_list()
        ret["durations"] = self.widgets["durations"].to_list()
        ret["gains"] = self.widgets["gains"].to_list()
        ret["compression"] = self.widgets["compression"].currentText()
        ret["compression_level"] = int(self.widgets["compression_level"].currentText())
        return ret

class CollectionModes(Qt.QWidget):
    def __init__(self, entries=None):
        super().__init__()
        self.layout = Qt.QVBoxLayout()
        self.layout.addWidget(Qt.QLabel("Collection Modes"))
        self.widgets = list()
        pushButton = Qt.QPushButton("New Entry")
        pushButton.clicked.connect(self.add_entry)
        self.layout.addWidget(pushButton)
        self.setLayout(self.layout)
        if entries is not None:
            for entry in entries:
                # print(f'Appending entry {entry}')
                new_entry = DictEntry(entry)
                self.widgets.append(new_entry)
                self.layout.addWidget(self.widgets[-1])
            return

    def add_entry(self):
        entry = DictEntry()
        entry.add_entry("name", placeholder="name of the mode")
        entry.add_entry("sample_rate", placeholder="sample rate of collection mode (samples/s)", conversion=float)
        entry.add_entry("duration", placeholder="duration (s)", conversion=float)
        entry.add_entry("gain", placeholder="gain of RX collection (dB)", conversion=float)
        self.widgets.append(entry)
        self.layout.addWidget(self.widgets[-1])

    def to_dict(self):
        dicts = [x.to_dict() for x in self.widgets]
        return {x["name"]: {k:v for k,v in x.items() if k != "name"} for x in dicts}


class SchedulingSlots(Qt.QWidget):
    def __init__(self, entries=None):
        super().__init__()
        self.layout = Qt.QVBoxLayout()
        self.layout.addWidget(Qt.QLabel("Scheduling slots"))
        self.widgets = list()
        pushButton = Qt.QPushButton("New Entry")
        pushButton.clicked.connect(self.add_entry)
        self.layout.addWidget(pushButton)
        self.setLayout(self.layout)
        if entries is not None:
            for entry in entries:
                # print(f'Appending entry {entry}')
                new_entry = DictEntry(entry)
                self.widgets.append(new_entry)
                self.layout.addWidget(self.widgets[-1])
            return

    def add_entry(self):
        entry = DictEntry()
        entry.add_entry("name", placeholder="name of the time slot")
        entry.add_entry("start", placeholder="start time (eg; 16:30)")
        entry.add_entry("end", placeholder="end time (eg; 18:30)")
        self.widgets.append(entry)
        self.layout.addWidget(self.widgets[-1])

    def to_dict(self):
        return {"time_slots": [x.to_dict() for x in self.widgets]}

class DictEntry(Qt.QWidget):
    def __init__(self, vals=None):
        super().__init__()
        self.layout = Qt.QVBoxLayout()
        self.params = {}

        self.setLayout(self.layout)
        if vals is not None:
            # print(f'{vals}')
            for k,v in vals.items():
                # print(f'Currently checking {k}: {v}')
                if isinstance(v, float):
                    # print(f'{v} is a float!')
                    conv = float
                elif isinstance(v,int):
                    conv = int
                else:
                    conv = str
                self.add_entry(k, str(v), conversion=conv)

    def add_entry(self, name, val=None, placeholder=None, conversion=str):
        widget = Qt.QLineEdit()
        widget.setSizePolicy(Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Minimum)
        widget.setMinimumSize(115, 20)
        if val is not None:
            widget.setText(val)
        if placeholder is not None:
            widget.setPlaceholderText(placeholder)
        self.params[name] = (widget, conversion)
        self.layout.addWidget(widget)

    def to_dict(self):
        ret = {}
        for k,(v,conv) in self.params.items():
            ret[k] = conv(v.displayText())
        return ret


class TitledListWidget(Qt.QWidget):
    def __init__(self, title="New List", items=None, conv=str):
        super().__init__()
        self.conv = conv
        self.layout = Qt.QVBoxLayout()
        self.layout.addWidget(Qt.QLabel(title))
        self.items = []
        add_item_button = Qt.QPushButton("Add Item")
        add_item_button.clicked.connect(lambda: self.add_item())
        self.layout.addWidget(add_item_button)
        if items is not None:
            for item in items:
                self.add_item(str(item))
        self.setLayout(self.layout)

    def add_item(self, item=""):
        self.items.append((Qt.QLineEdit(item)))
        self.layout.addWidget(self.items[-1])

    def to_list(self):
        return [self.conv(w.displayText()) for w in self.items]


def main():
    appctx = Qt.QApplication(sys.argv)
    app = App()
    app.show()
    sys.exit(appctx.exec_())
    

if __name__ == '__main__':
    main()
