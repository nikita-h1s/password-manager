from passm import create_app

app = create_app()


@app.route('/hello')
def hello():
    return 'Hello, World!'


if __name__ == '__main__':
    app.run(debug=True)
