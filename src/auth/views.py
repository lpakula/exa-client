from auth import bp


@bp.route("/", methods=['GET', 'POST'])
def connect():
    setting = Settings.query.get(1)
    if setting.connected:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        form = ConnectForm(request.form)
        if form.validate():
            status = ExAServerHelper(version=VERSION).connect(
                username=form.username.data, password=form.password.data)
            if status:
                flash('You have been connected with the server successfully.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash("You can't connect to the server with provided details. "
                      "Please make sure username and password are correct. "
                      "<br>Please check <a href='{}'> Logs </a> for more details.".format(
                        url_for('logs')), 'danger')
    form = ConnectForm()
    return render_template('connect.html', form=form)
