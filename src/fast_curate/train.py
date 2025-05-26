import PyQt6.QtWidgets as QtWidgets
from pathlib import Path
import pandas as pd
from spikeinterface.curation import train_model
from functools import partial
from datetime import datetime
print(
    '1: test-{date:%Y-%m-%d_%H:%M:%S}.txt'.format( date=datetime.now() )
    )
class TrainWindow(QtWidgets.QMainWindow):
    def __init__(self, project_folder, config):

        super().__init__()

        train_model_kwargs = {}


        window_title_text = "TIME TO TRAIN"
        self.setWindowTitle(window_title_text)

        global_curation_data_folder = project_folder / Path("curation_data")
        curation_data_folders = list(global_curation_data_folder.glob('*'))
        csv_paths = [curation_data_folder / "decision_data_with_metics.csv" for curation_data_folder in curation_data_folders]
        metrics = [pd.read_csv(csv_path) for csv_path in csv_paths]
        train_model_kwargs['metrics_paths'] = csv_paths

        metric_names_set = set()
        labels = []
        for metric_list in metrics:
            metric_names_for_one_sa = set(metric_list.columns)
            metric_names_set = metric_names_set.union(metric_names_for_one_sa)

            labels.append(metric_list["label"].values)

        train_model_kwargs['labels'] = labels
        train_model_kwargs['folder'] = project_folder / 'models' / 'model_{date:%Y-%m-%d_%H:%M:%S}.txt'.format( date=datetime.now() )  

        metric_names = [metric_name for metric_name in metric_names_set if metric_name not in ["index", "label", "unit_id"]]
        train_model_kwargs['metric_names'] = metric_names
  

        data_text = "Using the following data:<br />"
        for curation_data_folder, metric_data in zip(curation_data_folders, metrics):

            data_text += f"{curation_data_folder}: {len(metric_data)} units curated.<br />"

        data_text += f"<br />Metrics shared by all analyzer are: {metric_names}."

        print(data_text)

        formLayout = QtWidgets.QFormLayout()
        widget = QtWidgets.QWidget()
        widget.setStyleSheet("background-color: PeachPuff")
        label_1 = QtWidgets.QTextEdit(f"<h3>Information</h3><p>Here, we train many models based on the labelled data and choose the one with highest balanced accuracy.</p> <p>We train a model for each classifier, scalar and imputation method. This can add up quickly: if you have four classifiers, three scalar methods and two imputation method you'll end up running 4x3x2=24 tranings!</p> {data_text}")
        label_1.setReadOnly(True)
        label_1.setStyleSheet("background-color: white")

        blank_label = QtWidgets.QLabel("")

        self.classifiersForm = QtWidgets.QLineEdit("['RandomForestClassifier']")
        self.classifiersForm.setStyleSheet("background-color: white")
        classifiersOptions = QtWidgets.QLabel("<i>Possible options</i>: 'RandomForestClassifier', 'AdaBoostClassifier', 'GradientBoostingClassifier', 'SVC',<br /> 'LogisticRegression', 'XGBClassifier', 'CatBoostClassifier', 'LGBMClassifier', 'MLPClassifier'.")

        self.scalarsForm = QtWidgets.QLineEdit("['standard_scaler']")
        self.scalarsForm.setStyleSheet("background-color: white")

        scalarsOptions = QtWidgets.QLabel("<i>Possible options</i>: 'standard_scaler', 'min_max_scaler', 'robust_scaler'")

        self.imputersForm = QtWidgets.QLineEdit("['knn']")
        self.imputersForm.setStyleSheet("background-color: white")
        imputersOptions = QtWidgets.QLabel("<i>Possible options</i>: 'median', 'most_frequent', 'knn', 'iterative'")

        self.testSizeForm = QtWidgets.QLineEdit("0.2")
        self.testSizeForm.setStyleSheet("background-color: white")

        trainButton = QtWidgets.QPushButton("Train models")
        trainButton.clicked.connect(partial(self.do_training, train_model_kwargs))

        trainButton.setStyleSheet("background-color: red")

        formLayout.addRow(label_1)
        formLayout.addRow(blank_label)

        formLayout.addRow("List of Classifiers: ", self.classifiersForm)
        formLayout.addRow(classifiersOptions)
        formLayout.addRow(blank_label)

        formLayout.addRow("List of Scalars: ", self.scalarsForm)
        formLayout.addRow(scalarsOptions)
        formLayout.addRow(blank_label)

        formLayout.addRow("List of Imputers: ", self.imputersForm)
        formLayout.addRow(imputersOptions)
        formLayout.addRow(blank_label)

        formLayout.addRow("Test size: ", self.testSizeForm)
        formLayout.addRow(blank_label)

        formLayout.addRow(trainButton)




        widget.setLayout(formLayout)

        self.setCentralWidget(widget)


    def do_training(self, train_model_kwargs):

        imputation_strategies = eval(self.imputersForm.text())
        scaling_techniques = eval(self.scalarsForm.text())
        classifiers = eval(self.classifiersForm.text())
        test_size = eval(self.testSizeForm.text())

        print(imputation_strategies)

        train_model(
            mode="csv",
            imputation_strategies=imputation_strategies,
            scaling_techniques=scaling_techniques,
            classifiers=classifiers,
            test_size=test_size,
            **train_model_kwargs,
        )

        print(f"Finished training model. Saved in {train_model_kwargs['folder']}.")
