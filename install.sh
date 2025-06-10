#!/bin/bash
sudo apt update
sudo apt install uhd-host uhd-tools gnuradio gr-uhd python3-uhd python3-numpy
pip install zstandard
sudo uhd_images_downloader
sudo cp /usr/lib/uhd/utils/uhd-usrp.rules /etc/udev/rules.d/
echo "Setup complete! Log out and back in for permissions to take effect."
