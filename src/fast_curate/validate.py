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
from PyQt6.QtCore import Qt

pg.setConfigOption('background', 'w')

color_1 = (78, 121, 167)
color_2 = (242, 142, 43)
color_3 = (89, 161, 79)
color_3_fade = (169, 255, 146)

class UnitSelectionWidget(QtWidgets.QTableWidget):

    def __init__(self, table_data):
        
        super().__init__()

        #self.table_data = table_data

        self.setStyleSheet("background-color: white;")

        self.setColumnCount(4)
        headers = ["id", "Pred", "Conf", "New label"]
        self.setHorizontalHeaderLabels(headers)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.verticalHeader().setVisible(False)

        self.setRowCount(len(table_data))
    
        for row_index, (row_id, data) in enumerate(table_data.iterrows()):
            for col, col_name in enumerate(["unit_index", "prediction", "probability"]):#value in enumerate(data):
                value = data[col_name]
                if col == 2:

                    item = QtWidgets.QTableWidgetItem(str(round(value, ndigits=3)))
                else: 
                    item = QtWidgets.QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)                
                # Make confidence column sortable as numbers
                if col == 2:  # Confidence column
                    item.setData(Qt.ItemDataRole.UserRole, float(value))
                
                self.setItem(row_index, col, item)

        for a in range(3):
            self.horizontalHeader().setSectionResizeMode(a, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)


    def keyPressEvent(self, event): 

        keystroke = event.text()

        if keystroke in ['s','n']:
            current_row = self.currentRow()
            item = QtWidgets.QTableWidgetItem(str(keystroke))
            self.setItem(current_row, 3, item)
        else:
            super().keyPressEvent(event)

class ValidateWindow(QtWidgets.QMainWindow):

    update_signal = pyqtSignal()

    def __init__(self, labels, output_folder, analyzers, local_model, repo_model):

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


        analyzer_path = list(analyzers.values())[0]

        self.curation_display = self.load_and_display_analyzer(analyzer_path, labels, output_folder, local_model, repo_model)
    
        table_data = get_table_info(self.current_predicted_labels)
        self.unit_table_widget = UnitSelectionWidget(table_data)
        self.unit_table_widget.selectRow(0)
        self.unit_table_widget.itemSelectionChanged.connect(self.on_selection_changed)


        # self.random_button = QtWidgets.QPushButton("Show Random Unit")
        # self.random_button.clicked.connect(self.generate_random_integer)
        # validateLayout.addWidget(self.random_button,self.validateLayout_counter , 0)
        # self.validateLayout_counter += 1

        validateLayout.addWidget(self.unit_table_widget, self.validateLayout_counter, 0)
        self.validateLayout_counter += 1

        analyzersTitleWidget = QtWidgets.QLabel("Validate analyzers")
        analyzersTitleWidget.setStyleSheet("font-weight: bold; font-size: 20pt;")
        validateLayout.addWidget(analyzersTitleWidget, self.validateLayout_counter,0)
        self.validateLayout_counter += 1

        for i, analyzer in enumerate(analyzers.values()):

            curate_button = QtWidgets.QPushButton(f'Validate "{Path(analyzer).name}"')
            curate_button.clicked.connect(partial(self.load_new_analyzer, analyzer, labels, output_folder, local_model, repo_model))

            validateLayout.addWidget(curate_button,self.validateLayout_counter,0)
            self.validateLayout_counter += 1

        validateLayout.addWidget(self.curation_display, 0, 1, self.validateLayout_counter, 1)

        validateLayout.setColumnStretch(0, 1)
        validateLayout.setColumnStretch(1, 10)

        self.validateLayout = validateLayout

        widget.setLayout(validateLayout)
        self.setCentralWidget(widget)


    def on_selection_changed(self):
        current_row = self.unit_table_widget.currentRow()
        unit_id = int(self.unit_table_widget.item(current_row, 0).text())
        self.curation_display.update_to_unit(unit_id,unit_id)

    def load_and_display_analyzer(self, analyzer_path, labels, output_folder, local_model, repo_model):

        self.current_analyzer, have_extension = load_sa_and_extensions(analyzer_path)
        self.load_and_cache_model(self.current_analyzer, local_model, repo_model) 
        return CurationWidget(self.current_analyzer, labels, output_folder, have_extension, parent_window=self, initial_unit=0)


    def load_and_cache_model(self, sorting_analyzer, local_model, repo_model):

        if local_model is not None:
            self.current_predicted_labels = auto_label_units(sorting_analyzer=sorting_analyzer, model_folder=local_model)
        else:
            self.current_predicted_labels = auto_label_units(sorting_analyzer=sorting_analyzer, repo_id=repo_model, trust_model=True)

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


    def load_new_analyzer(self, analyzer_path, labels, output_folder, local_model, repo_model):

        self.validateLayout.removeWidget(self.curation_display)
        self.curation_display =  self.load_and_display_analyzer(analyzer_path, labels, output_folder, local_model, repo_model)
        self.validateLayout.addWidget(self.curation_display, 0, 1, 5, 1)


        self.validateLayout.removeWidget(self.unit_table_widget)
        table_data = get_table_info(self.current_predicted_labels)
        self.unit_table_widget = UnitSelectionWidget(table_data)
        self.unit_table_widget.selectRow(0)
        self.unit_table_widget.itemSelectionChanged.connect(self.on_selection_changed)

        self.validateLayout.addWidget(self.unit_table_widget, 0, 0, 1, 1)


def get_model_pred_and_conf(predicted_labels, a_random_unit):

    model_info = predicted_labels.query(f"index == {a_random_unit}")
    prediciton = model_info['prediction'].values[0]
    probability = model_info['probability'].values[0]

    return prediciton, probability

def get_table_info(predicted_labels):


    good_units= predicted_labels
    #good_units = predicted_labels.query("prediction == 's'")
    good_units['unit_index'] = good_units.index

    print(good_units)

    return good_units
    

   
