A spike curation tool, designed to be **fast** rather than flexible.

All good ideas/code stolen with love from [spikeinterface](https://github.com/SpikeInterface/spikeinterface) and [spikeinterface-gui](https://github.com/SpikeInterface/spikeinterface-gui). If you want a fully featured GUI which can be curation and much much much more, get spikeinterface-gui!!

# Installation

Recommended steps:

1. [install uv](https://docs.astral.sh/uv/getting-started/installation/#__tabbed_1_1)
2. Clone this repository and move into the repo folder:
```
git clone https://github.com/chrishalcrow/fast_curate.git
cd fast_curate
```
3. Try to run the environment 
```
uv run python
```

If that worked - great! You can now use `fast_curate`. 

# Run fast_curate

To run `fast_curate`, you need to specify:
* The labels you are going to use
* The path to your `sorting_analyzer`
* The path to your `output folder`

You should run the gui from your `fast_curate` (because this defines the python environment). Here's an example

```
uv run fast_curate/gui.py --labels sua mua noise --analyzer_path /home/Work/my_experiment/derivatives/M25/D20/kilosort4_sa --output_folder /home/Work/my_experiment/derivatives/M25/D20/kilosort4_sa/curation
```