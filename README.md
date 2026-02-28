git clone https://github.com/venkatsambath/AnamolyDetection.git
git checkout V1.0

dnf install -y python3.11
dnf install -y python3.11-pip
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
vi config.yaml
python3.11 run.py
