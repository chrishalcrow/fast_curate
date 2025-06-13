"""
    Controls the visualisation. All the GUI stuff!
"""

import json
import sys
from pathlib import Path
from argparse import ArgumentParser

import pandas as pd
import PyQt6.QtWidgets as QtWidgets
import numpy as np
import pyqtgraph as pg

from PyQt6.QtCore import pyqtSignal

import spikeinterface.full as si
from wrangle import DataForGUI

pg.setConfigOption('background', 'w')

color_1 = (78, 121, 167)
color_2 = (242, 142, 43)
color_3 = (89, 161, 79)
color_3_fade = (169, 255, 146)

def check_labels(labels):
    """Check that the user-inputted labels are unique and don't shadow special keys."""
    first_letters = [label[0] for label in labels]
    assert len(set(first_letters)) == len(
        first_letters), "Your labels must start with different letters"
    assert 'u' not in first_letters, "The key 'u' is reserved for (u)ndo. Please use a label which does not begin with 'u'"
    assert 'q' not in first_letters, "The key 'q' is reserved for (q)uit. Please use a label which does not begin with 'q'"

def check_and_maybe_delete_labels_file(final_result_path, output_folder):
    """If the output file of a curation already exists, asks the user if they'd like to delete it or not."""

    if final_result_path.is_file():
        yes_no_decision = "banana"
        while (yes_no_decision in ["y", "n"]) == False:
            yes_no_decision = input(
                'The `output_folder` already contains labelled output in `just_labels.csv`. Continuing will overwrite this file. Continue? (y/n) ')
            if yes_no_decision == "n":
                sys.exit()
            elif yes_no_decision == "y":
                final_result_path.unlink()
                results_with_metrics_path = output_folder / \
                    Path("decision_data_with_metics.csv")
                if results_with_metrics_path.is_file():
                    results_with_metrics_path.unlink()
                    return
    else:
        return

def load_sa_and_extensions(analyzer_path):
    """Loads the sorting analyzer and it's extensions"""

    print("\nLoading data...")
    have_extension = {}
    sorting_analyzer = si.load_sorting_analyzer(analyzer_path, load_extensions=False)
    missing_an_extension = False
    for extension in ['correlograms', 'unit_locations', 'templates', 'spike_amplitudes', 'spike_locations', 'quality_metrics', 'template_metrics']:
        have_extension[extension] = True
        try:
            sorting_analyzer.load_extension(extension)
        except:
            if missing_an_extension is False:
                print("")
            missing_an_extension = True
            have_extension[extension] = False
            print(f"    - No {extension} found. Will not display certain plots.")
    if missing_an_extension:
        print("")

    return sorting_analyzer, have_extension

def main():

    parser = ArgumentParser('Do a curation, quickly!')
    parser.add_argument(
        '--analyzer_path',
        type=Path,
        default='.',
        help="Path to a sorting analyzer that you'd like to curate"
    )
    parser.add_argument(
        '--labels',
        nargs='*',
        default=['sua', 'mua', 'noise']
    )
    parser.add_argument(
        '--output_folder',
        default=None,
        help="Path to folder for the labelled output"
    )

    args = parser.parse_args()

    analyzer_path = Path(args.analyzer_path)

    assert Path(args.analyzer_path).is_dir(
    ), "`analyzer_path` must be a directory."

    if args.output_folder is None:
        output_folder = analyzer_path / "curation"
    else:
        output_folder = Path(args.output_folder)
    
    assert Path(output_folder.parent).is_dir(
    ), "Parent folder of `output_folder` must already exist."
    output_folder.mkdir(exist_ok=True)

    final_result_path = output_folder / Path("just_labels.csv")
    check_and_maybe_delete_labels_file(final_result_path, output_folder)

    check_labels(args.labels)
    print(f"Your labels are {args.labels}. Your keystroke options are:\n\n\tq: quit\n\tu: undo")
    for label in args.labels:
        print(f"\t{label[0]}: {label}")

    sorting_analyzer, have_extension = load_sa_and_extensions(analyzer_path)

    app = QtWidgets.QApplication(sys.argv)
    window = CurationWindow(sorting_analyzer, args.labels,
                        output_folder, have_extension)
    window.resize(1600, 800)
    window.show()

    sys.exit(app.exec())


from PyQt6.QtGui import QPalette
from PyQt6.QtCore import Qt

class CurationWindow(QtWidgets.QMainWindow):

    update_signal = pyqtSignal()

    def __init__(self, sorting_analyzer, labels, output_folder, have_extension):

        # forward data from the user
        self.have_extension = have_extension
        self.output_folder = output_folder
        self.full_labels = labels
        self.first_letters = [label[0] for label in labels]

        # cache and wrangle data for all plots
        self.fs = sorting_analyzer.sampling_frequency
        self.data = DataForGUI(sorting_analyzer, have_extension)
        
        # set up unit id and tracking logic
        self.good_units = sorting_analyzer.unit_ids
        self.num_units = len(self.good_units)

        with open(output_folder / "num_units.txt", 'w') as num_units_file:
            num_units_file.write(str(self.num_units))

        self.id_1_tracker = 0
        self.curated_ids = []
        
        decision_data_path =  self.output_folder / Path("decision_data_with_metics.csv")
        if decision_data_path.is_file():
            previous_decision_data = pd.read_csv(decision_data_path)
            self.id_1_tracker = len(previous_decision_data)
            self.curated_ids = list(previous_decision_data['unit_id'].values)

        self.decision_counter = 0
        self.unit_id = self.good_units[self.id_1_tracker]

        # Make window
        super().__init__()

        window_title_text = "UNIT REFINE. Options: (q)uit, (u)ndo"
        for label in labels:
            window_title_text += f", ({label[0]}){label[1:]}"

        self.setWindowTitle(window_title_text)

        layout = QtWidgets.QGridLayout()
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)

        # Make widgets and arrange them in a grid.
        for a in [0, 1, 2, 3]:
            layout.setColumnStretch(a, 1)

        self.amp_raster_widget = pg.PlotWidget(self)
        self.loc_raster_widget = pg.PlotWidget(self)
        self.spike_locs_widget = pg.PlotWidget(self)
        self.max_template_widget = pg.PlotWidget(self)
        self.correlogram_widget = pg.PlotWidget(self)
        self.correlogram_zoom_widget = pg.PlotWidget(self)
        self.unit_locations_widget = pg.PlotWidget(self)
        self.all_templates_widget = pg.PlotWidget(self)
        self.binned_spikes_widget = pg.PlotWidget(self)

        layout.addWidget(self.unit_locations_widget, 0, 0)
        layout.addWidget(self.spike_locs_widget, 0, 1)
        layout.addWidget(self.max_template_widget, 0, 2)
        layout.addWidget(self.correlogram_widget, 0, 3)

        layout.addWidget(self.loc_raster_widget, 1, 0, 1, 2)
        layout.addWidget(self.all_templates_widget, 1, 2, 2, 1)
        layout.addWidget(self.correlogram_zoom_widget, 1, 3)

        layout.addWidget(self.amp_raster_widget, 2, 0, 1, 2)
        layout.addWidget(self.binned_spikes_widget, 2, 3)

        print("Starting plot...")

        self.initialise_plot()
        self.initialise_choice_df()

        self.setCentralWidget(widget)

    def initialise_plot(self):
        """Sets up the initial axes/plot styles for all plots, then plots the first unit."""

        self.unit_locations_widget.setXRange(
            self.data.unit_xmin, self.data.unit_xmax)
        self.unit_locations_widget.setYRange(
            self.data.unit_ymin, self.data.unit_ymax)
        self.unit_locations_plot_1 = self.unit_locations_widget.plot(
            self.data.channel_locations, pen=None, symbol="s", symbolSize=6)
        self.unit_locations_plot_2 = self.unit_locations_widget.plot(
            pen=None, symbol="o", symbolSize=6, symbolBrush=(50, 200, 200, 200))
        self.unit_locations_plot_3 = self.unit_locations_widget.plot(
            symbol="x", symbolSize=20, symbolBrush=color_2)
        self.unit_locations_widget.setLabels(
            title=f"UNIT {self.unit_id}/{self.num_units} -- Unit location")

        self.correlogram_plot = self.correlogram_widget.plot(
            stepMode="left", fillLevel=0, fillOutline=True, brush=color_1)
        self.correlogram_widget.setLabels(
            title="Auto-correlogram", bottom="time (ms)", left="count")

        self.correlogram_zoom_plot = self.correlogram_zoom_widget.plot(
            stepMode="left", fillLevel=0, fillOutline=True, brush=color_1)
        self.correlogram_zoom_widget.setLabels(
            title="Auto-correlograms (zoom out)", bottom="time (ms)", left="count")

        self.max_templates_plot = self.max_template_widget.plot(
            pen=pg.mkPen(color_3, width=3))
        self.max_template_widget.setLabels(
            title="Unit template on max channel", bottom="time (ms)", left="Signal (uV)")

        self.amps_raster_plot = self.amp_raster_widget.plot(
            pen=None, symbolPen=None, symbol="o", symbolBrush=color_3, symbolSize=4)
        self.amp_raster_widget.setLabels(
            title="Amplitude of spikes on max template channel", bottom="time (s)", left="Amplitude (uV)")

        self.locs_raster_plot = self.loc_raster_widget.plot(
            pen=None, symbolPen=None, symbol="o", symbolBrush=color_2, symbolSize=4)
        self.loc_raster_widget.setLabels(
            title="Location of spikes in time", bottom="time (s)", left="y-Location (um)")

        self.spike_locs_plot = self.spike_locs_widget.plot(
            pen=None, symbolPen=None, symbol="o", symbolBrush=color_2, symbolSize=4)
        self.spike_locs_widget.setLabels(
            title="Location of spikes in space", bottom="x (um)", left="y (um)")

        self.binned_spikes_plot = self.binned_spikes_widget.plot(
            stepMode="left", fillLevel=0, fillOutline=True, brush=color_1)
        self.binned_spikes_widget.setLabels(
            title="Binned spike counts", bottom=f"Bin number. Bin width = ", left="counts")

        self.all_templates_plot = self.all_templates_widget.plot(
            pen=pg.mkPen(color_3, width=2))
        self.all_templates_widget.setLabels(title="Unit templates (with standard deviation)")

        unit_data = self.data.get_unit_data(self.unit_id)
        self.update_plot(unit_data)

    def update_plot(self, unit_data):
        """Puts data into the plotting widgets."""

        if self.have_extension["spike_amplitudes"]:
            self.amps_raster_plot.setData(
                unit_data['spikes']/self.fs, unit_data['amps'])
        if self.have_extension["spike_locations"]:
            self.locs_raster_plot.setData(
                unit_data['spikes']/self.fs, unit_data['locs_y'])
            self.spike_locs_plot.setData(
                unit_data['locs_x'], unit_data['locs_y'])

        if self.have_extension["templates"]:
            self.max_templates_plot.setData(unit_data['template'])
            self.all_templates_widget.clear()
            self.update_template_plot(
                unit_data['channel_locations'], unit_data['scaled_templates'], unit_data['scaled_stds'])

        self.binned_spikes_plot.setData(
            unit_data['binned_spikes'])

        self.correlogram_plot.setData(
            unit_data['correlogram_bins'][1:], unit_data['correlograms'])
        self.correlogram_zoom_plot.setData(
            unit_data['wide_bins'][1:], unit_data['wide_correlograms'])

        if self.have_extension["unit_locations"]:
            self.unit_locations_plot_3.setData([unit_data['unit_location'][0]], [
                unit_data['unit_location'][1]])

        self.unit_locations_widget.setLabels(
            title=f"UNIT {self.unit_id}/{self.num_units} -- Unit location")

    def update_template_plot(self, channel_locations, all_templates, std_templates):
        """All templates plot is bit awkward, so factor out the messiness into a function. This function!"""

        template_channels_locs_1 = channel_locations[self.data.sparsity_mask[self.unit_id]]

        for template_index, template_channel_loc in enumerate(template_channels_locs_1):
            curve = pg.PlotCurveItem(4*template_channel_loc[0] + np.arange(
                90), template_channel_loc[1]/10 + all_templates[template_index, :], pen=pg.mkPen(color_3, width=2))
            curve_std_p = pg.PlotCurveItem(4*template_channel_loc[0] + np.arange(
                90), template_channel_loc[1]/10 + all_templates[template_index, :] + std_templates[template_index, :], pen=pg.mkPen(color_3_fade, width=1))
            curve_std_m = pg.PlotCurveItem(4*template_channel_loc[0] + np.arange(
                90), template_channel_loc[1]/10 + all_templates[template_index, :] - std_templates[template_index, :], pen=pg.mkPen(color_3_fade, width=1))
            pfill = pg.FillBetweenItem(curve_std_m, curve_std_p, brush=pg.mkBrush(color_3_fade))
            
            self.all_templates_widget.addItem(curve)
            self.all_templates_widget.addItem(pfill)
            self.all_templates_widget.addItem(curve_std_p, fillLevel=1)
            self.all_templates_widget.addItem(curve_std_m)

    # USER LOGIC

    def keyPressEvent(self, event): 

        keystroke = event.text()

        if keystroke in self.first_letters:
            self.curated_ids.append(self.unit_id)
            self.id_1_tracker += 1
        elif keystroke == "u":
            self.id_1_tracker -= 1
            if self.id_1_tracker == -1:
                print("Nothing to undo")
                self.id_1_tracker = 0
        elif keystroke == "q":
            self.close()
            return
        else:
            print(f"keystroke {keystroke} is not a valid option. Check the window title to see your options.")

        self.save_choice(keystroke)

        self.unit_id = self.good_units[self.id_1_tracker]
        unit_data = self.data.get_unit_data(self.unit_id)
        self.update_plot(unit_data)

    # SAVING STUFF

    def initialise_choice_df(self):
        """Make the initial `.csv` output file with appropriate column names."""

        string_to_write = "index,label,unit_id"
        for key in self.data.metrics.keys():
            string_to_write += f",{key}"
        string_to_write += "\n"

        decision_data_cache_path = self.output_folder / \
            Path("decision_data_cache.csv")
        if decision_data_cache_path.is_file():
            decision_data_cache_path.unlink()

        with open(decision_data_cache_path, 'w') as decision_file:
            decision_file.write(string_to_write)

    def save_choice(self, keystroke):
        """Add the user decision, including undo, to cache csv."""

        string_to_write = f"{self.decision_counter},{keystroke},{self.unit_id}"
        for values in self.data.metrics.iloc[self.unit_id].values:
            string_to_write += f",{values}"
        string_to_write += "\n"

        with open(self.output_folder / Path("decision_data_cache.csv"), 'a') as decision_file:
            decision_file.write(string_to_write)

        self.decision_counter += 1

    def save_labels(self, delete_decision_cache=False):
        """Converts the user decision cache into an output labels csv."""

        decision_data_with_metics_path = self.output_folder / Path("decision_data_with_metics.csv")
        decision_data_cache_path = self.output_folder / Path("decision_data_cache.csv")
        curated_ids = np.unique(self.curated_ids)
        
        previous_choices = pd.DataFrame()
        if decision_data_with_metics_path.is_file():
            previous_choices = pd.read_csv(decision_data_with_metics_path)

        new_choices = pd.read_csv(decision_data_cache_path)

        choices_to_save = pd.concat([previous_choices, new_choices])

        final_choices_list = []

        for unit_id in curated_ids:
            final_choices_list.append(choices_to_save.query(
                f'unit_id == {unit_id}').iloc[-1])
            
        print("final_choices_list: ", final_choices_list)

        keys = choices_to_save.keys()
        final_choices_df = pd.DataFrame(final_choices_list, columns=keys)
        final_choices_df = final_choices_df.rename(
            columns={'keystroke': 'label'})

        final_choices_df.to_csv(decision_data_with_metics_path, index=False)
        just_labels = final_choices_df[['unit_id', 'label']]
        just_labels.to_csv(self.output_folder /
                           Path("just_labels.csv"), index=False)
        
        if delete_decision_cache:
            decision_data_cache_path.unlink()
        
        self.make_spikeinterface_format(just_labels)

    def closeEvent(self, event):
        """Intercepts the user closing the app, to save the labels."""
        print("Saving final curation...")

        self.save_labels(delete_decision_cache=True)
        self.update_signal.emit()
        event.accept()

    def make_spikeinterface_format(self, labels):
        
        curation = {}
        curation["format_version"] = 1
        curation["unit_ids"] = []
        curation["label_definitions"] = {
            "quality": {
                "label_options": self.first_letters,
                "exclusive": "true"
            }
        }
        curation["manual_labels"] = []
        
        for _, (unit_id, label) in labels.iterrows():
            curation["unit_ids"].append(unit_id)
            curation["manual_labels"].append({"unit_id": str(unit_id), "quality": [label]})

        with open(self.output_folder / Path("spikeinterface_curation.yaml"), 'w') as si_file:
            json.dump(curation, si_file, indent=4)


if __name__ == '__main__':
    main()
