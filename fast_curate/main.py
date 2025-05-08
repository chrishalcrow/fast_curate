import sys
from pathlib import Path
import PyQt6.QtWidgets as QtWidgets
import yaml
from gui import CurationWindow, load_sa_and_extensions
from train import TrainWindow
import numpy as np

import PyQt6.QtWidgets as QtWidgets
import sys

from functools import partial

def add_analyzer(analyzers, directory):

    analyzer_keys = analyzers.keys()
    if len(analyzer_keys) > 0:
        max_key = np.max(list(analyzer_keys))
        new_key = max_key + 1
    else:
        new_key = 0

    analyzers[new_key] = directory

    return analyzers

def main():

    
    window.resize(1600, 800)
    window.show()

    sys.exit(app.exec())

class MainWindow(QtWidgets.QWidget):


    def __init__(self, output_folder, labels):
        
        super().__init__()
        
        self.w = None
        self.sorting_analyzer_paths = []
        self.curate_buttons = []
        self.delete_buttons = []

        self.output_folder = output_folder
        self.labels = labels

        self.config = {}
        self.config['labels'] = labels
        self.config['analyzers'] = {}

        saLayout = QtWidgets.QGridLayout(self)

        output_folder_text = QtWidgets.QLabel(f"Project folder: {self.output_folder}")
        saLayout.addWidget(output_folder_text,0,0,1,3)

        labels_text = QtWidgets.QLabel(f"Labels: {self.labels}")
        saLayout.addWidget(labels_text,1,0,1,3)

        self.add_sa_button = QtWidgets.QPushButton("+ Add Sorting Analyzer Folder")
        self.add_sa_button.clicked.connect(self.selectDirectoryDialog)
        saLayout.addWidget(self.add_sa_button,2,0,1,1)

        self.curate_text = QtWidgets.QLabel("Curated?")
        saLayout.addWidget(self.curate_text,3,1,1,1)

        self.curate_text = QtWidgets.QLabel("Remove")
        saLayout.addWidget(self.curate_text,3,2,1,1)
        
        trainLayout = QtWidgets.QGridLayout(self)

        self.train_button = QtWidgets.QPushButton("Train")
        self.train_button.clicked.connect(self.show_train_window)
        trainLayout.addWidget(self.train_button,2,3)

        validateLayout = QtWidgets.QGridLayout(self)

        self.validate_button = QtWidgets.QPushButton("Validate")
        self.validate_button.clicked.connect(self.show_validate_window)
        validateLayout.addWidget(self.validate_button,2,4)

        saWidget = QtWidgets.QWidget()
        trainWidget = QtWidgets.QWidget()
        validateWidget = QtWidgets.QWidget()

        saWidget.setStyleSheet("background-color: '#DCFFDC'")
        trainWidget.setStyleSheet("background-color: PeachPuff")
        validateWidget.setStyleSheet("background-color: Pink")

        self.saLayout = saLayout

        saWidget.setLayout(saLayout)
        trainWidget.setLayout(trainLayout)
        validateWidget.setLayout(validateLayout)

        self.layout = QtWidgets.QGridLayout(self)

        self.layout.addWidget(saWidget)
        self.layout.addWidget(trainWidget)
        self.layout.addWidget(validateWidget)


    def selectDirectoryDialog(self):
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setWindowTitle("Select Directory")
        file_dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        file_dialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)

        if file_dialog.exec():
            selected_directory = file_dialog.selectedFiles()[0]
            self.sorting_analyzer_paths.append(selected_directory)

            self.config['analyzers'] = add_analyzer(self.config['analyzers'], selected_directory)

            self.curate_buttons.append(QtWidgets.QPushButton(f'Curate "{selected_directory}"'))
            self.delete_buttons.append(QtWidgets.QPushButton(f"X"))

            for i, (curate_button, delete_button, (analyzer_index, selected_directory)) in enumerate(zip(self.curate_buttons, self.delete_buttons, self.config['analyzers'].items())):

                curate_button.clicked.connect(partial(self.show_curation_window, selected_directory, analyzer_index))
                self.saLayout.addWidget(curate_button,4+i,0)

                not_curated_text = QtWidgets.QLabel("No")
                self.saLayout.addWidget(not_curated_text,4+i,1)

                delete_button.clicked.connect(partial(self.remove_sa, selected_directory))
                self.saLayout.addWidget(delete_button,4+i,2)


        #self.curate_text
            
    def remove_sa(self, selected_directory):
        return

    def show_curation_window(self, selected_directory, analyzer_index):

        analyzer_path = Path(selected_directory)
        sorting_analyzer, have_extension = load_sa_and_extensions(analyzer_path)

        curation_output_folder = Path(self.output_folder) / Path(f"curation_data/{analyzer_index}_{analyzer_path.name}")
        curation_output_folder.mkdir(parents=False, exist_ok=True)

        with open(curation_output_folder / "sorting_analyzer_path.txt", "w") as f:
            f.write(str(selected_directory))

        #if self.w is None:
        self.w = CurationWindow(sorting_analyzer, self.labels, curation_output_folder, have_extension)
        self.w.resize(1600, 800)
        #else:
        #    print("Window already open!")

        self.w.show()

    def show_train_window(self, checked):
    #if self.w is None:
        self.w = TrainWindow(self.output_folder, self.config)
        self.w.resize(800, 600)
     #   else:
      #      print("Window already open!")

        self.w.show()
    def show_validate_window(self, checked):

        print("Coming soon...")



output_folder = Path("/home/nolanlab/Work/Developing/fromgit/fast_curate/my_project/")

with open(output_folder / "config.yaml") as stream:
    config = yaml.safe_load(stream)

labels = config['labels']

app = QtWidgets.QApplication(sys.argv)
from PyQt6.QtGui import QFont
custom_font = QFont()
custom_font.setFamily("courier new")
app.setFont(custom_font)
w = MainWindow(output_folder, labels)
w.show()
app.exec()

