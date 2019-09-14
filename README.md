# Pre-requisite

* python
* pip
* wkhtmltopdf (https://wkhtmltopdf.org/)
# Setup
```bash
$ pip install -r requirements.txt
```

# Run
The following command will generate a schedule in out.pdf
```bash
$ python main.py | wkhtmltopdf - out.pdf
```