import sys
import subprocess
import ast
import yaml
import json
from argparse import ArgumentParser

from pathlib import Path
from functools import partial

import pandas as pd

import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtWidgets import QStyleFactory
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from curate import load_sa_and_extensions
from train import TrainWindow
from spikeinterface.curation import auto_label_units

class UnitRefineProject():

    def __init__(self, folder_name):

        self.folder_name = folder_name
        self.analyzers = {}
        self.models = []
        self.config = {}

    def save(self, folder_name=None):

        if folder_name is None:
            folder_name = self.folder_name

        Path(folder_name).mkdir(exist_ok=True)

        Path(folder_name / "analyzers").mkdir(exist_ok=True)
        Path(folder_name / "models").mkdir(exist_ok=True)

        with open(folder_name / "config.json", 'w') as f:
            json.dump(self.config, f)

        for analyzer_name, analyzer_dict in self.analyzers.items():

            path = analyzer_dict.get('path')

            save_path = Path(folder_name / "analyzers" / f"{analyzer_name}_{Path(path).name}")
            save_path.mkdir(exist_ok=True)

            if path is not None:
                with open(save_path / 'path.txt', 'w') as output:
                    output.write(path)

            # metrics = analyzer_dict.get('metrics')
            # if metrics is not None:
            #     metrics.to_csv(save_path / 'metrics.csv')

            curation = analyzer_dict.get('labels')
            if curation is not None:
                curation.to_csv(save_path / 'labels.csv')


    def add_analyzer(self, directory):

        analyzer_keys = self.analyzers.keys()
        if len(analyzer_keys) > 0:
            max_key = max(list(analyzer_keys))
            new_key = max_key + 1
        else:
            new_key = 0

        self.analyzers[new_key] = {'path': directory}



def load_project(folder_name):

    folder_name = Path(folder_name)

    project = UnitRefineProject(folder_name)

    config_path = folder_name / "config.json"

    analyzers_folder = folder_name / "analyzers"
    analyzer_folders = list(analyzers_folder.glob('*/'))

    for analyzer_folder in analyzer_folders:

        analyzer_dict = {}

        with open(analyzer_folder / 'path.txt' ,"r") as f:
            analyzer_path = f.read()

        analyzer_dict['path'] = analyzer_path

        all_metrics = pd.read_csv(analyzer_folder / 'all_metrics.csv')
        analyzer_dict['all_metrics'] = all_metrics

        labelled_metrics = pd.read_csv(analyzer_folder / 'labelled_metrics.csv')
        analyzer_dict['labelled_metrics'] = labelled_metrics

        curation = pd.read_csv(analyzer_folder / 'labels.csv')
        analyzer_dict['labels'] = curation

        project.analyzers[analyzer_folder.name] = analyzer_dict
            
    models_folder = folder_name / "models"
    model_folders = list(models_folder.glob('*/'))

    for model_folder in model_folders:

        # models_dict = {}
        # models_dict['path'] = model_folder

        project.models.append(model_folder.name)

    return project
            

class MainWindow(QtWidgets.QWidget):

    def __init__(self, project):
        
        super().__init__()
        
        self.w = None
        self.sorting_analyzer_paths = []
        self.curate_buttons = []
        self.delete_buttons = []
        self.local_model = None
        self.repo_model = None

        self.output_folder = project.folder_name

        self.project = project

        # if config.get('labels') is not None:
        #     self.config['labels'] = config['labels']
        # else:
        #     self.config['labels'] = {}
        # self.labels = self.config['labels']

        # if config.get('analyzers') is not None:
        #     self.config['analyzers'] = config['analyzers']
        # else:
        #     self.config['analyzers'] = {}

        # for analyzer_path in self.config['analyzers'].values():
        #     if not Path(analyzer_path).is_dir():
        #         raise FileNotFoundError(f"Folder {analyzer_path} does not exist. Please update the config file at {output_folder / 'config.yaml'}.")

        # self.curation = config.get('curate')

        self.curation = True

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
            self.change_labels_button = QtWidgets.QLineEdit(f"good, SUA, MUA")
            # if self.config.get('labels') is not None:
            #     self.change_labels_button.setReadOnly(True)
            # else:
            #     self.change_labels_button.setStyleSheet("background-color: White")
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
        saLayout.addWidget(curationTitleWidget,0,0,1,1)
        
        self.add_sa_button = QtWidgets.QPushButton("+ Add Sorting Analyzer Folder")
        self.add_sa_button.clicked.connect(self.selectDirectoryDialog)
        saLayout.addWidget(self.add_sa_button,2,0,1,2)

        if self.curation:
            self.curate_text = QtWidgets.QLabel("Curated?")
            saLayout.addWidget(self.curate_text,3,2)

        
        self.saLayout = saLayout
        saWidget.setLayout(saLayout)
        self.make_curation_button_list(curation=self.curation)

        ###############
        # TRAIN
        ##############

        trainWidget = QtWidgets.QWidget()
        trainWidget.setStyleSheet("background-color: PeachPuff")

        self.trainLayout = QtWidgets.QGridLayout()

        trainTitleWidget = QtWidgets.QLabel("3. TRAIN")
        trainTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        self.trainLayout.addWidget(trainTitleWidget,0,0)

        train_button = QtWidgets.QPushButton("Train")
        train_button.clicked.connect(self.show_train_window)
        self.trainLayout.addWidget(train_button,1,0)

        trainTitleWidget = QtWidgets.QLabel("Choose your model:")
        #trainTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        self.trainLayout.addWidget(trainTitleWidget,2,0)


        self.make_train_list()

        trainWidget.setLayout(self.trainLayout)

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

        self.validateLayout = QtWidgets.QGridLayout()

        validateTitleWidget = QtWidgets.QLabel("4. VALIDATE AND REFINE")
        validateTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        self.validateLayout.addWidget(validateTitleWidget,0,0)

        self.make_validate_button_list()

        validateWidget.setLayout(self.validateLayout)

        
        self.main_layout.addWidget(saWidget)
        if self.curation:
            self.main_layout.addWidget(trainWidget)
        else: 
            self.main_layout.addWidget(applyWidget)
        self.main_layout.addWidget(validateWidget)

        ###############
        # CODE BUTTON
        ###############

        apply_code_button = QtWidgets.QPushButton("Generate code to apply model to analyzer")
        apply_code_button.clicked.connect(self.make_apply_code)
        self.main_layout.addWidget(apply_code_button)

    def get_local_models(self):

        models_folder = self.output_folder / "models"
        model_folders = list(models_folder.glob('*'))

        return model_folders

    def make_apply_code(self):

        if self.local_model is None and self.repo_model is None:
            models_folder = self.output_folder / "models"
            models = list([model_folder for model_folder in models_folder.glob('*') if str(model_folder.name).startswith('.') is False])
            self.local_model = models[0]

        code_text = "\n"
        code_text += "import spikinterface.full as si\n\n"
        code_text += "# point this path to the analyzer you want to apply the model to\n"
        code_text += "path_to_analyzer = 'path/to/analyzer'\n"
        code_text += "analyzer_to_curate = si.load_sorting_analyzer(path_to_analyzer)\n\n"
        if self.local_model is not None:
            code_text += f"model_folder = {self.local_model}\n\n"
            code_text += "# labels will be a list of curated labels, determined by the model.\n"
            code_text += "labels = si.auto_label_units(\n\tsorting_analyzer = analyzer_to_curate,\n\tmodel_folder = model_folder,\n)\n\n"
            code_text += "Read more here: https://spikeinterface.readthedocs.io/en/stable/tutorials/curation/plot_1_automated_curation.html\n\n"      

        elif self.repo_model is not None:
            code_text += f"repo_id = '{self.repo_model}'\n\n"
            code_text += "# labels will be a list of curated labels, determined by the model.\n"
            code_text += "labels = si.auto_label_units(\n    sorting_analyzer = analyzer_to_curate,\n    repo_id = repo_id,\n    trust_model = True,\n)\n\n"
            code_text += "Read more here: https://spikeinterface.readthedocs.io/en/stable/tutorials/curation/plot_1_automated_curation.html\n\n"      
        else:
            code_text = "No model loaded. Cannot apply to analyzer.\n\n"
            
        print(code_text)

    def selectDirectoryDialog(self):
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setWindowTitle("Select Directory")
        file_dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        file_dialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)

        if file_dialog.exec():
            selected_directory = file_dialog.selectedFiles()[0]

            if is_an_analyzer(selected_directory):

                self.project.add_analyzer(selected_directory)
                self.project.save()

                self.make_curation_button_list()
                self.make_validate_button_list()

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

        for analyzer_index, (analyzer_name, analyzer) in enumerate(self.project.analyzers.items()):

            selected_directory = analyzer['path']

            if len(str(selected_directory)) > 50:
               selected_directory_text_display = "..." + str(selected_directory)[-50:]
            else:
                selected_directory_text_display = selected_directory

            if self.curation:
                curate_button = QtWidgets.QPushButton(f'Curate "{selected_directory_text_display}"')
                curate_button.clicked.connect(partial(self.show_curation_window, selected_directory, analyzer_index))
                self.saLayout.addWidget(curate_button,4+analyzer_index,0,1,1)
        
                curation_output_folder = Path(self.project.folder_name) / Path(f"analyzers/{analyzer_index}_{Path(selected_directory).name}")
                curation_output_folder.mkdir(exist_ok=True)

                if (curation_output_folder / "num_units.txt").is_file():
                    just_labels = pd.read_csv(curation_output_folder / "decision_data_with_metics.csv")

                    with open(curation_output_folder / "num_units.txt", 'r') as file:
                        num_units = int(file.read())

                    not_curated_text = QtWidgets.QLabel(f"{len(just_labels)}/{num_units}")

                else:
                    not_curated_text = QtWidgets.QLabel("---")

                self.saLayout.addWidget(not_curated_text,4+analyzer_index,2)

            else:
                curate_button = QtWidgets.QLabel(f'"{selected_directory_text_display}"')
                self.saLayout.addWidget(curate_button,4+analyzer_index,0)

    def make_validate_button_list(self):

        for analyzer_index, (analyzer_name, analyzer) in enumerate(self.project.analyzers.items()):

            #print(f"{analyzer_index=}")

            selected_directory = analyzer['path']

            if len(str(selected_directory)) > 40:
               selected_directory_text_display = "..." + str(selected_directory)[-40:]
            else:
                selected_directory_text_display = selected_directory


            curate_button = QtWidgets.QPushButton(f'Validate "{selected_directory_text_display}"')
            curate_button.clicked.connect(partial(self.show_validate_window, selected_directory, analyzer_index))
            self.validateLayout.addWidget(curate_button,4+analyzer_index,0)

    def show_curation_window(self, selected_directory, analyzer_index):

        self.change_labels_button.setReadOnly(True)
        self.change_labels_button.setStyleSheet("background-color: LightBlue")

        analyzer_path = Path(selected_directory)

        print("Launching GUI in separate process...")
        # This will block until the external process closes
        print(f"{self.output_folder=}")
        subprocess.run([sys.executable, "/Users/christopherhalcrow/Work/fromgit/fast_curate/src/fast_curate/launch_sigui.py", analyzer_path, f'{self.output_folder}', f'{analyzer_index}'])
        print("GUI closed, resuming main app.")

    def show_train_window(self, checked):
        self.w = TrainWindow(self.project)
        self.w.resize(800, 600)
        self.w.show()

        self.w.update_signal.connect(self.make_train_list)

    def make_train_list(self):
        self.combo_box = QtWidgets.QComboBox(self)
        model_folders = self.get_local_models()
        model_names = [model_folder.name for model_folder in model_folders]
        self.combo_box.addItems(model_names)
        #self.combo_box.currentTextChanged.connect(self.selection_changed)
       
        self.trainLayout.addWidget(self.combo_box,3,0)

    def selection_changed(self, text):
        self.local_model = text
        print(f"{self.local_model=}")

    def show_validate_window(self, selected_directory, analyzer_index):

        analyzer_path = Path(selected_directory)
        sorting_analyzer, have_extension = load_sa_and_extensions(analyzer_path)

        current_model_name = self.combo_box.currentText()

        self.local_model = self.output_folder / "models" / current_model_name

        self.current_predicted_labels = auto_label_units(sorting_analyzer=sorting_analyzer, model_folder=self.local_model)

        model_labels_filepath = self.output_folder / f"analyzers/labels_from_{current_model_name}.csv"
        self.current_predicted_labels.to_csv(model_labels_filepath, index_label="unit_id")

        print("Launching GUI in separate process...")
        # This will block until the external process closes
        subprocess.run([sys.executable, "/Users/christopherhalcrow/Work/fromgit/fast_curate/src/fast_curate/launch_sigui_validate.py", analyzer_path, f'{self.output_folder}', f'{analyzer_index}', f'{model_labels_filepath}'])
        print("GUI closed, resuming main app.")

    def set_repo_model(self):
        self.local_model = None
        self.repo_model = self.repo_id_button.text()


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
        config_filepath = project_folder / "config.json"

        config = {}
        if project_folder.is_dir():
            print("Project already exists. Loading config file...")
            project = load_project(project_folder)
            # if config_filepath.is_file():
            #     with open(config_filepath) as stream:
            #         config = yaml.safe_load(stream)

        else:
            print("Project Folder does not exist. Creating now...")
            project = UnitRefineProject(project_folder)
            project.save()

        # if len(config) == 0:
        #     print("No config file found")
        #     if labels is None:
        #         config['labels'] = ['good', 'MUA', 'noise']
        #     else:
        #         config['labels'] = labels

        # curation_data_folder = project_folder / "curation_data"
        # curation_data_folder.mkdir(exist_ok=True)

        app = QtWidgets.QApplication(sys.argv)

        app.setStyle(QStyleFactory.create("Fusion"))

        custom_font = QFont()
        custom_font.setFamily("courier new")
        app.setFont(custom_font)
        w = MainWindow(project)
        w.setWindowTitle('UnitRefine')
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


if __name__ == "__main__":
    main()
