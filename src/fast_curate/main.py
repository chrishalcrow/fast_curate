import sys
import subprocess
import ast
import json
from argparse import ArgumentParser

from pathlib import Path
from functools import partial

import pandas as pd

import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtWidgets import QStyleFactory
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt

from train import TrainWindow
from spikeinterface.curation import auto_label_units
from spikeinterface.core import load_sorting_analyzer

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

            curation = analyzer_dict.get('labels')
            if curation is not None:
                curation.to_csv(save_path / 'labels.csv')

    def add_analyzer(self, directory):

        analyzer_keys = self.analyzers.keys()
        if len(analyzer_keys) > 0:
            #analyzer_keys_ints = [int(key) for key in analyzer_keys]
            max_key = max(list(analyzer_keys))
            new_key = max_key + 1
        else:
            new_key = 0

        analyer_in_project = Path(f'analyzers/{new_key}_{Path(directory).name}')
        self.analyzers[new_key] = {'path': directory, 'analyzer_in_project': analyer_in_project}


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

        analyzer_dict['analyzer_in_project'] = f"analyzers/{Path(analyzer_folder).name}"

        project.analyzers[int(str(analyzer_folder.name).split('_')[0])] = analyzer_dict
            
    models_folder = folder_name / "models"
    model_folders = [folder for folder in list(models_folder.glob('*/')) if '.DS' not in str(folder)]
    print(f"{model_folders=}")

    for model_folder in model_folders:

        project.models.append(model_folder)

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
        self.make_curation_button_list()

        ###############
        # TRAIN
        ##############

        trainWidget = QtWidgets.QWidget()
        trainWidget.setStyleSheet("background-color: PeachPuff")

        self.trainLayout = QtWidgets.QGridLayout()

        trainTitleWidget = QtWidgets.QLabel("3. TRAIN or LOAD models")
        trainTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        self.trainLayout.addWidget(trainTitleWidget,0,0)

        train_button = QtWidgets.QPushButton("Train")
        train_button.clicked.connect(self.show_train_window)
        self.trainLayout.addWidget(train_button,1,0)

        train_button = QtWidgets.QPushButton("+ Load")
        train_button.clicked.connect(self.selectModelDialog)
        self.trainLayout.addWidget(train_button,1,1)

        trainWidget.setLayout(self.trainLayout)

        ###############
        # VALIDATE
        ##############

        validateWidget = QtWidgets.QWidget()
        validateWidget.setStyleSheet("background-color: Pink")

        self.validateLayout = QtWidgets.QGridLayout()

        validateTitleWidget = QtWidgets.QLabel("4. VALIDATE AND REFINE")
        validateTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        self.validateLayout.addWidget(validateTitleWidget,0,0)

        trainTitleWidget = QtWidgets.QLabel("Choose your model:")
        #trainTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        self.validateLayout.addWidget(trainTitleWidget,1,0)

        self.make_model_list()

        trainTitleWidget = QtWidgets.QLabel("And try it on an analyzer:")
        #trainTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        self.validateLayout.addWidget(trainTitleWidget,3,0)

        self.make_validate_button_list()

        validateWidget.setLayout(self.validateLayout)

        self.main_layout.addWidget(saWidget)
        if self.curation:
            self.main_layout.addWidget(trainWidget)
        self.main_layout.addWidget(validateWidget)

        ###############
        # CODE BUTTON
        ###############

        print(f"{self.project.models=}")

        apply_code_button = QtWidgets.QPushButton("Generate code to apply model to analyzer")
        apply_code_button.clicked.connect(self.make_apply_code)
        self.main_layout.addWidget(apply_code_button)




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
                print("hello adding a model!")
                self.project.models = [selected_directory] + self.project.models
                self.make_model_list()
            else:
                print(f"{selected_directory} is not a UnitRefine model folder.")
            
    def make_curation_button_list(self):

        for analyzer_index, (analyzer_name, analyzer) in enumerate(self.project.analyzers.items()):

            selected_directory = analyzer['path']

            if len(str(selected_directory)) > 50:
               selected_directory_text_display = "..." + str(selected_directory)[-50:]
            else:
                selected_directory_text_display = selected_directory

            if self.curation:

                curate_button = QtWidgets.QPushButton(f'Curate "{selected_directory_text_display}"')
                curate_button.clicked.connect(partial(self.show_curation_window, selected_directory, analyzer_index))
                self.saLayout.addWidget(curate_button,4+analyzer_index,0)
        
                curation_output_folder = Path(self.project.folder_name) / Path(f"analyzers/{analyzer_index}_{Path(selected_directory).name}")
                curation_output_folder.mkdir(exist_ok=True)

                if (curation_output_folder / "all_metrics.csv").is_file():
                    just_labels = pd.read_csv(curation_output_folder / "labels.csv")
                    all_metrics = pd.read_csv(curation_output_folder / "all_metrics.csv")

                    not_curated_text = QtWidgets.QLabel(f"{len(just_labels)}/{len(all_metrics)}")

                else:

                    not_curated_text = QtWidgets.QLabel("---")

                self.saLayout.addWidget(not_curated_text,4+analyzer_index,2)

            else:
                curate_button = QtWidgets.QLabel(f'"{selected_directory_text_display}"')
                self.saLayout.addWidget(curate_button,4+analyzer_index,0)

    def make_validate_button_list(self):

        for analyzer_index, (analyzer_name, analyzer) in enumerate(self.project.analyzers.items()):

            selected_directory = analyzer['path']

            if len(str(selected_directory)) > 40:
               selected_directory_text_display = "..." + str(selected_directory)[-40:]
            else:
                selected_directory_text_display = selected_directory

            curate_button = QtWidgets.QPushButton(f'Validate "{selected_directory_text_display}"')
            curate_button.clicked.connect(partial(self.show_validate_window, analyzer))
            self.validateLayout.addWidget(curate_button,4+analyzer_index,0)

    def show_curation_window(self, selected_directory, analyzer_index):

        self.change_labels_button.setReadOnly(True)
        self.change_labels_button.setStyleSheet("background-color: LightBlue")

        analyzer_path = Path(selected_directory)

        print("\nLaunching GUI in separate process...")
        print(f"{self.output_folder=}")
        subprocess.run([sys.executable, "/Users/christopherhalcrow/Work/fromgit/fast_curate/src/fast_curate/launch_sigui.py", analyzer_path, f'{self.output_folder}', f'{analyzer_index}'])
        print("GUI closed, resuming main app.\n")

    def show_train_window(self, checked):
        self.w = TrainWindow(self.project)
        self.w.resize(800, 600)
        self.w.show()
        self.w.update_signal.connect(self.make_model_list)

    def make_model_list(self):
        self.combo_box = QtWidgets.QComboBox(self)
        model_folders = [Path(model) for model in self.project.models]
        model_names = [model_folder.name for model_folder in model_folders]
        self.combo_box.addItems(model_names)       
        self.validateLayout.addWidget(self.combo_box,2,0)

    def show_validate_window(self, analyzer):

        analyzer_path = Path(analyzer['path'])
        sorting_analyzer = load_sorting_analyzer(analyzer_path, load_extensions=False)

        current_model_name = self.combo_box.currentText()

        self.local_model = [model for model in self.project.models if str(current_model_name) in str(model)][0]

        #self.local_model = self.output_folder / "models" / current_model_name

        self.current_predicted_labels = auto_label_units(sorting_analyzer=sorting_analyzer, model_folder=self.local_model, trust_model=True)

        analyzer_in_project = analyzer['analyzer_in_project']

        model_labels_filepath = f"{self.output_folder / analyzer_in_project / 'labels_from_{current_model_name}.csv'}"
        self.current_predicted_labels.to_csv(model_labels_filepath, index_label="unit_id")

        print("Launching GUI in separate process...")
        # This will block until the external process closes
        subprocess.run([sys.executable, "/Users/christopherhalcrow/Work/fromgit/fast_curate/src/fast_curate/launch_sigui_validate.py", analyzer_path, f'{self.output_folder}', f'{analyzer_in_project}', f'{model_labels_filepath}'])
        print("GUI closed, resuming main app.")

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

        args = parser.parse_args()        
        project_folder = Path(args.project_folder).resolve()

        if project_folder.is_dir():
            print("Project already exists. Loading...")
            project = load_project(project_folder)
        else:
            print("Project Folder does not exist. Creating now...")
            project = UnitRefineProject(project_folder)
            project.save()

        app = QtWidgets.QApplication(sys.argv)

        app.setStyle(QStyleFactory.create("Fusion"))

        icon_file = Path(__file__).absolute().parent / 'resources' / 'logo.png'
        if icon_file.exists():
            app.setWindowIcon(QIcon(str(icon_file)))

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

def is_a_model(directory):

    if (Path(directory) / "best_model.skops").is_file():
        return True
    
    return False

if __name__ == "__main__":
    main()
