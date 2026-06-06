from flask import Flask, render_template, request, redirect, url_for, flash
from database import get_db_connection, init_db
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'expense_tracker_secret_key'

# Initialize the database when app starts
with app.app_context():
    init_db()

# ─── HOME / DASHBOARD ───────────────────────────────────────────
@app.route('/')
def dashboard():
    conn = get_db_connection()
    
    # Get all expenses
    expenses = conn.execute(
        'SELECT * FROM expenses ORDER BY date DESC'
    ).fetchall()
    
    # Calculate total
    total = conn.execute(
        'SELECT SUM(amount) as total FROM expenses'
    ).fetchone()['total'] or 0
    
    # Monthly summary
    monthly = conn.execute(
        '''SELECT strftime('%Y-%m', date) as month, 
           SUM(amount) as total, COUNT(*) as count
           FROM expenses 
           GROUP BY month 
           ORDER BY month DESC'''
    ).fetchall()
    
    # Category summary
    categories = conn.execute(
        '''SELECT category, SUM(amount) as total, COUNT(*) as count
           FROM expenses 
           GROUP BY category 
           ORDER BY total DESC'''
    ).fetchall()
    
    conn.close()
    return render_template('dashboard.html', 
                           expenses=expenses, 
                           total=total,
                           monthly=monthly,
                           categories=categories)

# ─── ADD EXPENSE ─────────────────────────────────────────────────
@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        title    = request.form['title']
        amount   = request.form['amount']
        category = request.form['category']
        date     = request.form['date']
        notes    = request.form['notes']

        if not title or not amount or not category or not date:
            flash('Please fill in all required fields!', 'error')
            return redirect(url_for('add_expense'))

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO expenses (title, amount, category, date, notes) VALUES (?, ?, ?, ?, ?)',
            (title, float(amount), category, date, notes)
        )
        conn.commit()
        conn.close()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('dashboard'))

    today = datetime.today().strftime('%Y-%m-%d')
    return render_template('add_expense.html', today=today)

# ─── EDIT EXPENSE ────────────────────────────────────────────────
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    conn = get_db_connection()
    expense = conn.execute(
        'SELECT * FROM expenses WHERE id = ?', (id,)
    ).fetchone()

    if request.method == 'POST':
        title    = request.form['title']
        amount   = request.form['amount']
        category = request.form['category']
        date     = request.form['date']
        notes    = request.form['notes']

        conn.execute(
            '''UPDATE expenses 
               SET title=?, amount=?, category=?, date=?, notes=?
               WHERE id=?''',
            (title, float(amount), category, date, notes, id)
        )
        conn.commit()
        conn.close()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    conn.close()
    return render_template('edit_expense.html', expense=expense)

# ─── DELETE EXPENSE ──────────────────────────────────────────────
@app.route('/delete/<int:id>')
def delete_expense(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM expenses WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Expense deleted!', 'success')
    return redirect(url_for('dashboard'))

# ─── SEARCH ──────────────────────────────────────────────────────
@app.route('/search')
def search():
    query    = request.args.get('q', '')
    category = request.args.get('category', '')
    conn     = get_db_connection()

    if query and category:
        expenses = conn.execute(
            '''SELECT * FROM expenses 
               WHERE (title LIKE ? OR notes LIKE ?) AND category = ?
               ORDER BY date DESC''',
            (f'%{query}%', f'%{query}%', category)
        ).fetchall()
    elif query:
        expenses = conn.execute(
            '''SELECT * FROM expenses 
               WHERE title LIKE ? OR notes LIKE ?
               ORDER BY date DESC''',
            (f'%{query}%', f'%{query}%')
        ).fetchall()
    elif category:
        expenses = conn.execute(
            'SELECT * FROM expenses WHERE category = ? ORDER BY date DESC',
            (category,)
        ).fetchall()
    else:
        expenses = conn.execute(
            'SELECT * FROM expenses ORDER BY date DESC'
        ).fetchall()

    conn.close()
    return render_template('search.html', 
                           expenses=expenses, 
                           query=query, 
                           category=category)
# ─── DOWNLOAD CSV ────────────────────────────────────────────────
@app.route('/download')
def download_expenses():
    import csv
    import io
    from flask import Response

    conn = get_db_connection()
    expenses = conn.execute(
        'SELECT title, amount, category, date, notes FROM expenses ORDER BY date DESC'
    ).fetchall()
    conn.close()

    def generate():
        data = io.StringIO()
        writer = csv.writer(data)
        # Write header row
        writer.writerow(['Title', 'Amount', 'Category', 'Date', 'Notes'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        # Write data rows
        for expense in expenses:
            writer.writerow([
                expense['title'],
                expense['amount'],
                expense['category'],
                expense['date'],
                expense['notes'] or ''
            ])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    return Response(
        generate(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=expenses.csv'}
    )
if __name__ == '__main__':
    app.run(debug=True)