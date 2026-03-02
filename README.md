
````md
# AnomalyDetection Setup Guide

## 1. Clone the Repository

```
git clone https://github.com/venkatsambath/AnamolyDetection.git
cd AnamolyDetection
git checkout V1.0
````

---

## 2. Install Python 3.11 (RHEL / CentOS )

```
dnf install -y python3.11
dnf install -y python3.11-pip
```

---

## 3. Create and Activate Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

---

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 5. Update Configuration

Edit the configuration file:

```bash
vi config.yaml
```

Modify parameters as needed.

---

## 6. Run the Application

```bash
python3.11 run.py
```

---

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
