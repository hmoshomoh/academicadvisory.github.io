# Academic Support & Complaints Management System

A web application for a college. It does two things:

1. **Academic support** — students see their GPA and CGPA worked out from their results, and the system automatically generates advice based on how they are doing.
2. **Complaints** — students report problems either under their name or completely anonymously, and staff work through them with a permanent record of every action taken.

Built with Python, Django and PostgreSQL.

---

## Part 1 — Set it up on your computer

Follow these steps in order. Each one is a command you type into a terminal, then press Enter.

### Step 1: Check you have what you need

Type each of these and press Enter. Each should print a version number.

```bash
python3 --version
```

```bash
psql --version
```

```bash
git --version
```

If `python3` is missing, install Python 3 from https://www.python.org/downloads/.
If `psql` is missing, install PostgreSQL from https://www.postgresql.org/download/.
If `git` is missing, install Git from https://git-scm.com/downloads.

### Step 2: Download the code

```bash
git clone https://github.com/hmoshomoh/academicadvisory.github.io.git
```

```bash
cd academicadvisory.github.io
```

Stay in this folder for every remaining step.

### Step 3: Create a private space for the project's add-ons

```bash
python3 -m venv .venv
```

This makes a folder called `.venv`. It keeps this project's add-ons separate from the rest of your computer.

### Step 4: Switch into that space

On **Mac or Linux**:

```bash
source .venv/bin/activate
```

On **Windows**:

```bash
.venv\Scripts\activate
```

Your terminal prompt should now start with `(.venv)`. **You must do this step every time you open a new terminal to work on this project.** If the prompt does not say `(.venv)`, the later commands will fail.

### Step 5: Install the add-ons

```bash
pip install -r requirements.txt
```

Wait for it to finish. It downloads Django and six other packages.

### Step 6: Make sure PostgreSQL is running

On **Mac** (if you installed it with Homebrew):

```bash
brew services start postgresql
```

On **Linux**:

```bash
sudo service postgresql start
```

On **Windows**, PostgreSQL usually starts by itself after installation.

To check it worked:

```bash
pg_isready
```

You want to see `accepting connections`.

### Step 7: Create the database

```bash
createdb acad_app
```

This creates an empty database named `acad_app`. It prints nothing if it worked — that is normal.

If it says the database already exists, that is fine. Move on.

### Step 8: Build the tables inside the database

```bash
python manage.py migrate
```

You will see a list of lines ending in `OK`.

### Step 9: Create the user roles and complaint categories

```bash
python manage.py bootstrap_roles
```

This creates the three roles (Student, Adviser, Admin) and the five complaint categories. It ends with `Roles and categories are in place.`

This command is safe to run again at any time.

### Step 10: Add demo data so you have something to look at

```bash
python manage.py seed_demo
```

This creates three students, one adviser, one admin, their results, and some sample complaints. It prints the login details at the end.

**Skip this step if you are setting up for real use** and want to start with an empty system. If you skip it, go to "Creating your own admin account" near the bottom of this file.

### Step 11: Start the application

```bash
python manage.py runserver
```

Leave this running. Open your web browser and go to:

```
http://localhost:8000
```

To stop the application later, click back on the terminal and press `Ctrl` and `C` together.

---

## Part 2 — Log in and use it

After running `seed_demo` in Step 10, you have these accounts. **The password for all of them is `Walkthrough!2026`.**

| Username | Role | What you will see |
| --- | --- | --- |
| `csc2022001` | Student | A CGPA of 4.69 and positive course advice |
| `csc2022002` | Student | A CGPA of 2.38 and a warning |
| `csc2022003` | Student | A CGPA of 0.88 and a probation alert |
| `adviser1` | Adviser | All three students above, assigned to them |
| `admin1` | Admin | Every complaint, the dashboard and the export |

Log in at `http://localhost:8000/accounts/login/`. The system sends you to the correct starting page based on your role — there is no separate login page per role.

### As a student

**To see your academic standing:**

1. Log in as `csc2022003`.
2. You land on **My academics**.
3. Your CGPA is in the box at the top left.
4. Below, each semester is listed with its courses, credit units, grades and that semester's GPA.
5. Under each semester is the recommendation the system generated for it.

**To ask your adviser a question:**

1. Click **Ask my adviser**.
2. Type a subject and your question.
3. Click **Send request**.
4. The reply will appear on your **My academics** page once your adviser answers.

**To report a problem:**

1. Click **Submit a complaint** in the top menu.
2. Choose a category from the dropdown.
3. Type a subject and describe what happened.
4. Attach a file if you have evidence. Allowed types: PDF, PNG, JPG, JPEG, TXT, DOCX. Maximum size 5MB.
5. **Decide whether to tick "Submit this anonymously".** Read the next section before you decide.
6. Click **Submit complaint**.
7. The next screen shows your **tracking reference**, which looks like `ACS-QCYV5SKXTS`. **Write it down or screenshot it now.**

**To check on a complaint you already sent:**

- Click **Track a complaint** in the top menu, type in your reference, and click **Check status**. This works even when logged out, and on any device.
- If you sent it under your name, you can also click **My complaints** to see it in a list.

### Named or anonymous — what actually changes

**If you leave the box unticked (named):**

- The complaint is linked to your account.
- It appears in your **My complaints** list.
- Admins can see your name and matric number.
- You get a notification in the app whenever the status changes.

**If you tick the box (anonymous):**

- Your identity is **never recorded anywhere**. It is not hidden or restricted — it is simply never written down.
- The complaint will **not** appear in your **My complaints** list. The system genuinely cannot find it for you.
- Admins see only the word "Anonymous".
- Your name will not appear in any exported report.
- **Your tracking reference is the only way to check on it.** Nobody — including administrators — can look it up for you if you lose it.

That last point is the trade-off, and it is deliberate. It is what makes the anonymity genuine rather than a setting someone could switch off.

### As an adviser

1. Log in as `adviser1`. You land on **My students**.
2. You see only the students assigned to you, with their CGPAs.
3. Click **Records** beside any student to see their full semester history and recommendations.
4. Click **Advisory requests** in the top menu to see questions students have sent you.
5. Click **Respond**, type your reply, and click **Send response**. The student sees it on their own page.

Advisers cannot see complaints at all. This is intentional, since complaints may concern staff.

### As an admin

1. Log in as `admin1`. You land on the complaints list.
2. Use the two dropdowns to filter by status or category, then click **Filter**.
3. Click **Open** beside a complaint to work on it.

On the complaint page you can do four things. **Each one permanently records who did it and when:**

| Action | What it does | Needs |
| --- | --- | --- |
| **Update category** | Moves it to the right queue | A category |
| **Mark under review** | Says you are looking into it | Nothing (note optional) |
| **Escalate** | Sends it up to someone senior | A reason |
| **Resolve** | Closes it | A resolution note |

Scroll to the bottom of any complaint to see the **audit trail** — every action in order, with the name of the staff member and the time. Entries in this trail can never be edited or deleted by anyone.

**To see the statistics:**

1. Click **Dashboard** in the top menu.
2. You see total complaints, how many are still open, how many were anonymous, and the average time taken to resolve one.
3. Below that: a chart of complaints by category and a table by status.

**To download a report:**

Click **Export CSV** on either the dashboard or the complaints list. A spreadsheet file downloads. You can open it in Excel or Google Sheets. Anonymous complaints show "Anonymous" in the submitter column.

**To enter a student's exam results:**

1. Go to `http://localhost:8000/django-admin/`.
2. Click **Academic records**, then **ADD ACADEMIC RECORD** at the top right.
3. Choose the student, type the session (for example `2024/2025`) and pick the semester.
4. In the rows below, type each course code, title, credit units and grade.
5. Click **Save**.
6. The GPA and the recommendation are calculated immediately. The student sees them straight away.

**To assign a student to an adviser:**

1. Go to `http://localhost:8000/django-admin/`.
2. Click **Students**, then click the student's name.
3. Choose an adviser from the **Adviser** dropdown.
4. Click **Save**.

---

## How grades are calculated

A 5.0-point scale.

| Grade | A | B | C | D | E | F |
| --- | --- | --- | --- | --- | --- | --- |
| Points | 5 | 4 | 3 | 2 | 1 | 0 |

**GPA** (one semester) = add up (credit units × grade points) for every course, then divide by the total credit units.

Worked example — a student takes a 3-unit course and gets an A, and a 1-unit course and gets an F:

```
(3 × 5) + (1 × 0) = 15
15 ÷ 4 units = 3.75 GPA
```

Note this is **not** the same as averaging 5 and 0 to get 2.50. Courses worth more credit units count for more.

**CGPA** = the same calculation applied to every course from every semester at once. It is not an average of the GPAs.

A student with no results recorded shows `—` rather than an error.

## How recommendations are decided

The system writes these automatically from the GPA. Nobody types them.

| GPA for that semester | Recommendation generated |
| --- | --- |
| 2.50 and above | **Course advice** — keep the current study pattern, consider electives |
| 1.50 to 2.49 | **Warning** — prioritise weak courses, see your adviser |
| Below 1.50 | **Probation alert** — at risk of probation, reduce course load, see your adviser |

Any course the student failed is named in the message as a retake list.

If a grade is corrected later, the recommendation updates itself and any advice that no longer applies is removed.

---

## Creating your own admin account

If you skipped the demo data in Step 10, create an administrator for yourself:

```bash
python manage.py createsuperuser
```

Answer the username, email and password prompts. Then give that account the Admin role:

1. Start the application with `python manage.py runserver`.
2. Go to `http://localhost:8000/django-admin/`.
3. Log in with the account you just made.
4. Click **Users**, then your username.
5. Scroll to **Groups**, select **Admin** from the left box, and click the arrow to move it to the right box.
6. Click **Save**.

Students create their own accounts using the **Register** link on the site. They are placed in the Student role automatically.

To create an adviser: make the user account in **Users**, add them to the **Adviser** group the same way as above, then go to **Advisers** and add a record linking that user to a staff number.

---

## Running the tests

```bash
python manage.py test
```

41 tests. They take about a minute and a half. You should see `OK` at the end.

---

## Putting it online

This runs on any hosting service that offers PostgreSQL — Render, Railway or Fly.io. The `Procfile` tells the host what to run.

Set these five environment variables in your hosting dashboard:

| Variable | What to put |
| --- | --- |
| `SECRET_KEY` | A long random string. Generate one with: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | Your site's address, for example `myapp.onrender.com` |
| `DATABASE_URL` | Your host provides this when you add a PostgreSQL database |
| `CSRF_TRUSTED_ORIGINS` | Your full address, for example `https://myapp.onrender.com` |

Two things to know:

- **This cannot run on GitHub Pages.** GitHub Pages only serves fixed files; this application needs Python and a database running on a server.
- **Uploaded attachments are stored as files on the server.** Most hosting services wipe those files on each redeploy. The complaints survive; the attached photos may not. Add a persistent disk through your host if you need them kept.

---

## If something goes wrong

**`command not found: python3`** — Python is not installed. See Step 1.

**`django-admin: command not found` or `No module named django`** — you are not in the virtual space. Run the Step 4 command again and check your prompt shows `(.venv)`.

**`connection refused` or `could not connect to server`** — PostgreSQL is not running. See Step 6.

**`database "acad_app" does not exist`** — you skipped Step 7.

**`relation "accounts_student" does not exist`** — you skipped Step 8.

**`That port is already in use`** — the application is already running in another terminal. Either use that one, or start this one on a different port with `python manage.py runserver 8001` and visit `http://localhost:8001`.

**The page says "Forbidden (403)"** — you are logged in as the wrong role for that page. Log out and log in as an account that has the right role.

---

## How the project is organised

| Folder | What is inside |
| --- | --- |
| `accounts/` | Registration, login, the three roles, students and advisers |
| `academics/` | Results, GPA/CGPA calculation, recommendations, advisory requests |
| `complaints/` | Complaint submission, tracking, the admin workflow, the audit trail |
| `notifications/` | Status-change notices |
| `templates/` | Every page's layout |
| `config/` | Settings and the list of web addresses |

Two files are worth reading if you want to understand the rules:

- `academics/grading.py` — the grade scale and thresholds, defined once, nowhere else.
- `complaints/services.py` — the only place a complaint can be changed, so the audit trail and the notification can never be skipped.

`EXPECTATIONS.md` lists every requirement from the original specification and how each one was checked.
