"""
    Controls the visualisation. All the GUI stuff!
"""

from curate import CurationWidget, load_sa_and_extensions
import PyQt6.QtWidgets as QtWidgets
import pyqtgraph as pg
from pathlib import Path
from PyQt6.QtCore import pyqtSignal
from spikeinterface.curation import load_model, auto_label_units
import numpy.random as rand
from functools import partial

pg.setConfigOption('background', 'w')

color_1 = (78, 121, 167)
color_2 = (242, 142, 43)
color_3 = (89, 161, 79)
color_3_fade = (169, 255, 146)

class ValidateWindow(QtWidgets.QMainWindow):

    update_signal = pyqtSignal()

    def __init__(self, labels, output_folder, analyzers):

        output_folder = Path(output_folder)

        # Make window
        super().__init__()

        window_title_text = "UNIT REFINE."

        self.setWindowTitle(window_title_text)

        validateLayout = QtWidgets.QGridLayout()

        self.validateLayout_counter = 0

        widget = QtWidgets.QWidget()
        widget.setStyleSheet("background-color: Pink")

        models_folder = output_folder / "models"
        models = list([model_folder for model_folder in models_folder.glob('*') if str(model_folder.name).startswith('.') is False])

        self.current_model_path = models[0]

        analyzer_path = list(analyzers.values())[0]

        self.curation_display = self.load_and_display_analyzer(analyzer_path, self.current_model_path, labels, output_folder)

        self.unit_info_widget = QtWidgets.QTextEdit("")
        self.unit_info_widget.setReadOnly(True)
        self.unit_info_widget.setStyleSheet("background-color: white")

        self.random_button = QtWidgets.QPushButton("Generate Random Unit")
        self.random_button.clicked.connect(self.generate_random_integer)
        validateLayout.addWidget(self.random_button,self.validateLayout_counter , 0)
        self.validateLayout_counter += 1


        validateLayout.addWidget(self.unit_info_widget, self.validateLayout_counter, 0)
        self.validateLayout_counter += 1

        analyzersTitleWidget = QtWidgets.QLabel("Validate analyzers")
        analyzersTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        validateLayout.addWidget(analyzersTitleWidget, self.validateLayout_counter,0)
        self.validateLayout_counter += 1

        for i, analyzer in enumerate(analyzers.values()):

            curate_button = QtWidgets.QPushButton(f'Validate "{Path(analyzer).name}"')
            curate_button.clicked.connect(partial(self.load_new_analyzer, analyzer, labels, output_folder))

            validateLayout.addWidget(curate_button,self.validateLayout_counter,0)
            self.validateLayout_counter += 1

        modelsTitleWidget = QtWidgets.QLabel("Validate models")
        modelsTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        validateLayout.addWidget(modelsTitleWidget, self.validateLayout_counter,0)
        self.validateLayout_counter += 1

        for model_path in models:

            print(f"adding model_path {model_path}")

            model_button = QtWidgets.QPushButton(f'Validate "{model_path.name}"')
            model_button.clicked.connect(partial(self.load_new_model, model_path))

            validateLayout.addWidget(model_button,self.validateLayout_counter,0)
            self.validateLayout_counter += 1

        validateLayout.addWidget(self.curation_display, 0, 1, self.validateLayout_counter, 1)

        validateLayout.setColumnStretch(0, 1)
        validateLayout.setColumnStretch(1, 3)

        self.validateLayout = validateLayout

        widget.setLayout(validateLayout)
        self.setCentralWidget(widget)



    def load_and_display_analyzer(self, analyzer_path, model_path, labels, output_folder):

        self.current_analyzer, have_extension = load_sa_and_extensions(analyzer_path)
        self.load_and_cache_model(model_path, self.current_analyzer)        
        return CurationWidget(self.current_analyzer, labels, output_folder, have_extension, parent_window=self, initial_unit=0)
        


    def load_and_cache_model(self, model_path, sorting_analyzer):

        self.current_predicted_labels = auto_label_units(sorting_analyzer=sorting_analyzer, model_folder=model_path)
        self.current_num_units = len(self.current_predicted_labels)



    def load_new_model(self, model_path):

        self.load_and_cache_model(model_path, self.current_analyzer)
        self.generate_random_integer()



    def generate_random_integer(self):
        # Generate a random integer between 1 and 100
        random_int = rand.randint(1, self.current_num_units)
        
        self.curation_display.unit_id = random_int
        self.curation_display.update_to_unit(random_int)

        prediction, confidence = get_model_pred_and_conf(self.current_predicted_labels, random_int)

        self.unit_info_widget.setText(f"Unit {random_int}.<br />Pred: {prediction}.<br />Confidence: {confidence}")


    def load_new_analyzer(self, analyzer_path, labels, output_folder):

        self.validateLayout.removeWidget(self.curation_display)
        self.curation_display =  self.load_and_display_analyzer(analyzer_path, self.current_model_path, labels, output_folder)
        self.validateLayout.addWidget(self.curation_display, 0, 1, 5, 1)

def get_model_pred_and_conf(predicted_labels, a_random_unit):

    model_info = predicted_labels.query(f"index == {a_random_unit}")
    prediciton = model_info['prediction'].values[0]
    probability = model_info['probability'].values[0]

    return prediciton, probability

