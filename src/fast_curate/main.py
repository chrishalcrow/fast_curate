import sys
import ast
import yaml
import json
from argparse import ArgumentParser

from pathlib import Path
from functools import partial

import pandas as pd

import PyQt6.QtWidgets as QtWidgets
from PyQt6.QtWidgets import QStyleFactory
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from curate import CurationWindow, load_sa_and_extensions
from train import TrainWindow
from validate import ValidateWindow


class MainWindow(QtWidgets.QWidget):

    def __init__(self, output_folder, config):
        
        super().__init__()
        
        self.w = None
        self.sorting_analyzer_paths = []
        self.curate_buttons = []
        self.delete_buttons = []
        self.local_model = None
        self.repo_model = None

        self.output_folder = output_folder

        self.config = {}

        if config.get('labels') is not None:
            self.config['labels'] = config['labels']
        else:
            self.config['labels'] = {}
        self.labels = self.config['labels']

        if config.get('analyzers') is not None:
            self.config['analyzers'] = config['analyzers']
        else:
            self.config['analyzers'] = {}

        self.curation = config.get('curate')

        self.main_layout = QtWidgets.QGridLayout(self)

        to_curateWidget = QtWidgets.QWidget()
        to_curateWidget.setStyleSheet("background-color: LightBlue")

        to_curateLayout = QtWidgets.QGridLayout()

        if self.curation is not None:
            self.set_rest_of_page()
        else:

            ###############
            # WHICH ONE?
            ##############

            ManualButton = QtWidgets.QPushButton("Manually curate\n and Train")
            ManualButton.clicked.connect(self.set_curation_true)
            to_curateLayout.addWidget(ManualButton,0,0)

            OrLabel = QtWidgets.QLabel("OR")
            OrLabel.setStyleSheet("font-size: 20pt;")
            OrLabel.setAlignment(Qt.AlignmentFlag.AlignCenter) 
            to_curateLayout.addWidget(OrLabel,0,1)

            ApplyExistingButton = QtWidgets.QPushButton("Apply\n existing Model")
            ApplyExistingButton.clicked.connect(self.set_curation_false)

            to_curateLayout.addWidget(ApplyExistingButton,0,2)

            to_curateWidget.setLayout(to_curateLayout)

            self.main_layout.addWidget(to_curateWidget)


    def set_curation_true(self):
        self.curation=True
        self.config['curate'] = self.curation
        self.main_layout.removeWidget(self.main_layout.itemAt(0).widget())
        self.set_rest_of_page()

    def set_curation_false(self):
        self.curation=False
        self.config['curate'] = self.curation
        self.main_layout.removeWidget(self.main_layout.itemAt(0).widget())
        self.set_rest_of_page()

    def set_rest_of_page(self):

        

        projectWidget = QtWidgets.QWidget()
        projectWidget.setStyleSheet("background-color: LightBlue")

        projectLayout = QtWidgets.QGridLayout()

        projectTitleWidget = QtWidgets.QLabel("1. PROJECT DETAILS")
        projectTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        projectLayout.addWidget(projectTitleWidget, 0, 0)

        output_folder_text = QtWidgets.QLabel(f"Project folder: {self.output_folder}")
        projectLayout.addWidget(output_folder_text,1,0,1,3)

        if self.curation:
            labels_text = QtWidgets.QLabel("Labels: ")
            labels_text.setAlignment(Qt.AlignmentFlag.AlignRight) 
            projectLayout.addWidget(labels_text,2,0,1,1)
            self.change_labels_button = QtWidgets.QLineEdit(f"{self.labels}")
            if self.config.get('labels') is not None:
                self.change_labels_button.setReadOnly(True)
            else:
                self.change_labels_button.setStyleSheet("background-color: White")
            projectLayout.addWidget(self.change_labels_button,2,1,1,2)

        projectWidget.setLayout(projectLayout)
        
        self.main_layout.addWidget(projectWidget)

        ###############
        # CURATE
        ##############

        saWidget = QtWidgets.QWidget()
        saWidget.setStyleSheet("background-color: '#CBEECB'")

        saLayout = QtWidgets.QGridLayout()
        
        curation_title_text = "2. CURATION" if self.curation else "2. ADD ANALYZERS"

        curationTitleWidget = QtWidgets.QLabel(curation_title_text)
        curationTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        saLayout.addWidget(curationTitleWidget)
        
        self.add_sa_button = QtWidgets.QPushButton("+ Add Sorting Analyzer Folder")
        self.add_sa_button.clicked.connect(self.selectDirectoryDialog)
        saLayout.addWidget(self.add_sa_button,2,0,1,1)

        if self.curation:
            self.curate_text = QtWidgets.QLabel("Curated?")
            saLayout.addWidget(self.curate_text,3,1,1,1)

            self.reset_text = QtWidgets.QLabel("Reset")
            saLayout.addWidget(self.reset_text,3,2,1,1)
        
        self.saLayout = saLayout
        saWidget.setLayout(saLayout)
        self.make_curation_button_list(curation=self.curation)

        ###############
        # TRAIN
        ##############

        trainWidget = QtWidgets.QWidget()
        trainWidget.setStyleSheet("background-color: PeachPuff")

        trainLayout = QtWidgets.QGridLayout()

        trainTitleWidget = QtWidgets.QLabel("3. TRAIN")
        trainTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        trainLayout.addWidget(trainTitleWidget,0,0)

        train_button = QtWidgets.QPushButton("Train")
        train_button.clicked.connect(self.show_train_window)
        trainLayout.addWidget(train_button,1,0)

        trainWidget.setLayout(trainLayout)

        ###############
        # APPLY MODEL
        ##############

        applyWidget = QtWidgets.QWidget()
        applyWidget.setStyleSheet("background-color: PeachPuff")

        applyLayout = QtWidgets.QGridLayout()

        applyTitleWidget = QtWidgets.QLabel("3. APPLY MODEL")
        applyTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        applyLayout.addWidget(applyTitleWidget,0,0,1,2)

        load_model_button = QtWidgets.QPushButton("+ Load local model")
        load_model_button.clicked.connect(self.selectModelDialog)
        applyLayout.addWidget(load_model_button,1,0,1,3)

        # apply_local_model = QtWidgets.QPushButton("Apply")
        # apply_local_model.clicked.connect(self.set_local_model)
        # applyLayout.addWidget(apply_local_model,1,2,1,1)

        applyTitleWidget = QtWidgets.QLabel("OR")
        applyTitleWidget.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        applyTitleWidget.setStyleSheet("font-size: 20pt;")
        applyLayout.addWidget(applyTitleWidget,2,0,1,3)


        repo_id_text = QtWidgets.QLabel("Repo ID: ")
        repo_id_text.setAlignment(Qt.AlignmentFlag.AlignRight) 
        applyLayout.addWidget(repo_id_text,3,0,1,1)
        self.repo_id_button = QtWidgets.QLineEdit(f"spikeinterface/blah-blah")
        self.repo_id_button.setStyleSheet("background-color: white")
        applyLayout.addWidget(self.repo_id_button,3,1,1,1)

        apply_repo_model = QtWidgets.QPushButton("Apply")
        apply_repo_model.clicked.connect(self.set_repo_model)
        applyLayout.addWidget(apply_repo_model,3,2,1,1)

        applyWidget.setLayout(applyLayout)


        ###############
        # VALIDATE
        ##############

        validateWidget = QtWidgets.QWidget()
        validateWidget.setStyleSheet("background-color: Pink")

        validateLayout = QtWidgets.QGridLayout()

        validateTitleWidget = QtWidgets.QLabel("4. REFINE AND VALIDATE")
        validateTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        validateLayout.addWidget(validateTitleWidget,0,0)

        self.validate_button = QtWidgets.QPushButton("Validate")
        self.validate_button.clicked.connect(self.show_validate_window)
        validateLayout.addWidget(self.validate_button,1,0)

        validateWidget.setLayout(validateLayout)

        
        self.main_layout.addWidget(saWidget)
        if self.curation:
            self.main_layout.addWidget(trainWidget)
        else: 
            self.main_layout.addWidget(applyWidget)
        self.main_layout.addWidget(validateWidget)

    def selectDirectoryDialog(self):
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setWindowTitle("Select Directory")
        file_dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        file_dialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)

        if file_dialog.exec():
            selected_directory = file_dialog.selectedFiles()[0]

            if is_an_analyzer(selected_directory):

                self.sorting_analyzer_paths.append(selected_directory)

                self.config['analyzers'] = add_analyzer(self.config['analyzers'], selected_directory)

                with open(self.output_folder / 'config.yaml', 'w') as file:
                    yaml.dump(self.config, file)

                self.make_curation_button_list()

            else:

                print(f"Selected directory {selected_directory} is not a SortingAnalyzer.")

    
    def selectModelDialog(self):
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setWindowTitle("Select Directory")
        file_dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        file_dialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)

        if file_dialog.exec():
            selected_directory = file_dialog.selectedFiles()[0]

            if is_a_model(selected_directory):

                self.local_model = selected_directory

            else:

                print(f"Selected directory {selected_directory} is not a model.")
            
    def make_curation_button_list(self, curation=False):

        for i, (analyzer_index, selected_directory) in enumerate(self.config['analyzers'].items()):

            if len(str(selected_directory)) > 40:
               selected_directory_text_display = "..." + str(selected_directory)[-40:]
            else:
                selected_directory_text_display = selected_directory

            if self.curation:
                curate_button = QtWidgets.QPushButton(f'Curate "{selected_directory_text_display}"')
                curate_button.clicked.connect(partial(self.show_curation_window, selected_directory, analyzer_index))
                self.saLayout.addWidget(curate_button,4+i,0)
        
                delete_button = QtWidgets.QPushButton("X")

                curation_output_folder = Path(self.output_folder) / Path(f"curation_data/{analyzer_index}_{Path(selected_directory).name}")
                curation_output_folder.mkdir(exist_ok=True)

                if (curation_output_folder / "num_units.txt").is_file():
                    just_labels = pd.read_csv(curation_output_folder / "just_labels.csv")

                    with open(curation_output_folder / "num_units.txt", 'r') as file:
                        num_units = int(file.read())

                    not_curated_text = QtWidgets.QLabel(f"{len(just_labels)}/{num_units}")

                else:
                    not_curated_text = QtWidgets.QLabel("---")

                self.saLayout.addWidget(not_curated_text,4+i,1)

                delete_button.clicked.connect(partial(self.reset_sa, curation_output_folder))
                self.saLayout.addWidget(delete_button,4+i,2)

            else:
                curate_button = QtWidgets.QLabel(f'"{selected_directory_text_display}"')
                self.saLayout.addWidget(curate_button,4+i,0)

    def reset_sa(self, selected_directory):

        files_in_dir = list(selected_directory.glob('*'))
        for curation_file in files_in_dir:
            if curation_file.is_file():
                curation_file.unlink()

        self.make_curation_button_list()

    def show_curation_window(self, selected_directory, analyzer_index):

        self.labels = parse_labels(self.change_labels_button.text())
        self.config['labels'] = self.labels
        with open(self.output_folder / 'config.yaml', 'w') as file:
            yaml.dump(self.config, file)

        self.change_labels_button.setReadOnly(True)
        self.change_labels_button.setStyleSheet("background-color: LightBlue")

        analyzer_path = Path(selected_directory)
        sorting_analyzer, have_extension = load_sa_and_extensions(analyzer_path)

        curation_output_folder = Path(self.output_folder) / Path(f"curation_data/{analyzer_index}_{analyzer_path.name}")
        curation_output_folder.mkdir(parents=False, exist_ok=True)

        self.curation_output_folder = curation_output_folder

        with open(curation_output_folder / "sorting_analyzer_path.txt", "w") as f:
            f.write(str(selected_directory))

        self.w = CurationWindow(sorting_analyzer, self.labels, curation_output_folder, have_extension)
        self.w.resize(1600, 800)

        self.w.update_signal.connect(self.make_curation_button_list)

        self.w.show()


    def show_train_window(self, checked):
        self.w = TrainWindow(self.output_folder, self.config)
        self.w.resize(800, 600)
        self.w.show()

    def show_validate_window(self, checked):

        self.w = ValidateWindow(self.labels, self.output_folder, self.config['analyzers'], self.local_model, self.repo_model)
        self.w.resize(1600, 800)
        self.w.show()

    def set_repo_model(self):
        self.local_model = None
        self.repo_model = self.repo_id_button.text()


def add_analyzer(analyzers, directory):

    analyzer_keys = analyzers.keys()
    if len(analyzer_keys) > 0:
        max_key = max(list(analyzer_keys))
        new_key = max_key + 1
    else:
        new_key = 0

    analyzers[new_key] = directory

    return analyzers

def parse_labels(labels_string):

   parsed_list = ast.literal_eval(labels_string)

   return parsed_list

def main():
        
    if __name__ == "__main__":
        
        parser = ArgumentParser(
            description="UnitRefine - curate your sorting and create a machine learning model based on your curation."
        )
        parser.add_argument(
            "--project_folder",
            required=True,
            type=str,
        )
        parser.add_argument(
            "--labels",
            nargs='+',
        )

        args = parser.parse_args()
        
        labels = args.labels
        project_folder = Path(args.project_folder).resolve()
        config_filepath = project_folder / "config.yaml"

        config = {}
        if project_folder.is_dir():
            print("Project already exists. Loading config file...")
            if config_filepath.is_file():
                with open(config_filepath) as stream:
                    config = yaml.safe_load(stream)

                if labels is not None:
                    inputted_labels = labels
                    if labels != config['labels']:
                        print(f"User inputted labels {inputted_labels} do not match labels in config file {config['labels']}")
                        print("Using labels in config file.")
        else:
            print("Project Folder does not exist. Creating now...")
            project_folder.mkdir()

        if len(config) == 0:
            print("No config file found")
            if labels is None:
                print("No labels specified. Using 'good', 'bad'")
                config['labels'] = ['good', 'bad']
            else:
                config['labels'] = labels

        curation_data_folder = project_folder / "curation_data"
        curation_data_folder.mkdir(exist_ok=True)

        app = QtWidgets.QApplication(sys.argv)

        app.setStyle(QStyleFactory.create("Fusion"))

        custom_font = QFont()
        custom_font.setFamily("courier new")
        app.setFont(custom_font)
        w = MainWindow(project_folder, config)
        w.show()
        app.exec()


def is_an_analyzer(directory):

    directory = Path(directory)

    if (directory / "spikeinterface_info.json").is_file():
        with open(directory / "spikeinterface_info.json") as f:
            info = json.load(f)
        if info.get("object") == "SortingAnalyzer":
            return True
    
    return False

def is_a_model(directory):

    return True

if __name__ == "__main__":
    main()



