import PyQt6.QtWidgets as QtWidgets
from pathlib import Path
import pandas as pd
from spikeinterface.curation import train_model
from functools import partial
from datetime import datetime

class TrainWindow(QtWidgets.QMainWindow):
    def __init__(self, project_folder, config):

        super().__init__()

        train_model_kwargs = {}

        window_title_text = "UNITREFINE: Train your model"
        self.setWindowTitle(window_title_text)

        self.model_folder = None

        global_curation_data_folder = project_folder / Path("curation_data")
        curation_data_folders = [f for f in global_curation_data_folder.glob('*') if not str(f.name).startswith('.')]
        csv_paths = [str(curation_data_folder / "decision_data_with_metics.csv") for curation_data_folder in curation_data_folders]
        metrics = [pd.read_csv(csv_path) for csv_path in csv_paths]
        train_model_kwargs['metrics_paths'] = csv_paths

        metric_names_set = set()
        labels = []
        for metric_list in metrics:
            metric_names_for_one_sa = set(metric_list.columns)
            if len(metric_names_set) == 0:
                metric_names_set = metric_names_for_one_sa
            else:
                metric_names_set = metric_names_set.intersection(metric_names_for_one_sa)

            labels.append(list(metric_list["label"].values))

        train_model_kwargs['labels'] = labels
        parent_folder = project_folder / 'models' 

        metric_names = [metric_name for metric_name in metric_names_set if metric_name not in ["index", "label", "unit_id"]]
        train_model_kwargs['metric_names'] = metric_names

        data_text = "Using the following analyzers:<br />"
        for curation_data_folder, metric_data in zip(curation_data_folders, metrics):

            data_text += f"{curation_data_folder}: {len(metric_data)} units curated.<br />"

        data_text += f"<br />Metrics shared by all analyzer are: {metric_names}."

        formLayout = QtWidgets.QFormLayout()
        widget = QtWidgets.QWidget()
        widget.setStyleSheet("background-color: PeachPuff")
        label_1 = QtWidgets.QTextEdit(f"<h3>Information</h3><p>Here, you can train many models based on the labelled data.</p>{data_text}")
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
        trainButton.clicked.connect(partial(self.do_training, train_model_kwargs, parent_folder))

        codeButton = QtWidgets.QPushButton("Generate code to train a model")
        codeButton.clicked.connect(partial(self.generate_code, train_model_kwargs, parent_folder))

        #trainButton.setStyleSheet("")

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
        formLayout.addRow(codeButton)

        widget.setLayout(formLayout)

        self.setCentralWidget(widget)

    def generate_code(self, train_model_kwargs, parent_folder):

        model_folder = parent_folder / 'model_{date:%Y-%m-%d_%H:%M:%S}'.format( date=datetime.now() )

        code_text = "\n# Here is the code being executed by the 'Train Model' button above\n"
        code_text += "# Feel free to play with the different arguments!\n\n"
        code_text += "import spikeinterface.full as si\n\n"
        code_text += f"model = si.train_model(\n    mode='csv',\n     imputation_strategies={eval(self.imputersForm.text())},\n    scaling_techniques={eval(self.scalarsForm.text())},\n    classifiers={eval(self.classifiersForm.text())},\n    test_size={eval(self.testSizeForm.text())},\n    folder={model_folder}\n"
        for key, value in train_model_kwargs.items():
            code_text += f"    {key} = {value},\n"
        code_text += ")\n\n"
        code_text += f"# Your model is saved at {model_folder}\n\n"
        code_text += "Read more here: https://spikeinterface.readthedocs.io/en/stable/tutorials/curation/plot_2_train_a_model.html\n\n"      

        print(code_text)


    def do_training(self, train_model_kwargs, parent_folder):

        imputation_strategies = eval(self.imputersForm.text())
        scaling_techniques = eval(self.scalarsForm.text())
        classifiers = eval(self.classifiersForm.text())
        test_size = eval(self.testSizeForm.text())

        folder = parent_folder / 'model_{date:%Y-%m-%d_%H:%M:%S}'.format( date=datetime.now() )  

        train_model(
            mode="csv",
            imputation_strategies=imputation_strategies,
            scaling_techniques=scaling_techniques,
            classifiers=classifiers,
            test_size=test_size,
            folder=folder,
            **train_model_kwargs,
        )

        print(f"Finished training models. Best model saved in in {folder}.")

        self.model_folder = folder
