# BetProject

## Preface
BetProject is a Django-based application designed to manage user accounts, roles, and financial transactions in a hierarchical structure. The project leverages Django's robust framework to provide a secure and scalable solution for managing user roles, permissions, and financial operations such as deposits, withdrawals, and account statements , bet placement, ledgers , P&L etc.

## Business Logic
The core business logic revolves around managing user roles and their hierarchical relationships. The application supports various roles, each with specific permissions and responsibilities. Financial transactions are tracked and managed at the account level, ensuring transparency and accountability. The system also includes features for generating partnership deeds, managing commissions, and handling user authentication and authorization.

And, Second Part comes under the sports sections where user will place bet for two sports such as cricket and casino from getting data from the AWS and then all the arthemtic operations and calculations will be done at the backend level for the integrity and transparency among users and each level.

### Key Features Completed
- Role-based access control
- Financial transaction management
- Partnership deed generation
- User authentication and authorization
- Dynamic role hierarchy

### Key features Pending
- ledger
- Bet placement
- P & L
- Maintain account Book of each user at every level

## Roles and Restrictions
The application defines the following roles:

| Role        | Level |
|-------------|-------|
| Superadmin  | 100   |
| Subadmin    | 90    |
| Admin       | 80    |
| Miniadmin   | 70    |
| Master      | 60    |
| Super       | 50    |
| Agent       | 40    |
| Client      | 30    |

### Role Hierarchy
Roles are organized in a hierarchical structure, where higher-level roles have more permissions. For example, a Superadmin can manage all other roles, while a Client has the least permissions.

### Restrictions
- Lower-level roles cannot access or modify data belonging to higher-level roles.
- Financial operations are restricted based on role permissions.
- Partnership deeds and commissions are managed dynamically based on the role hierarchy.

## Database Schema
The database schema is designed to support the hierarchical structure of roles and financial transactions. Below is the SQL representation of the schema:

```sql
CREATE TABLE User (
    id INTEGER PRIMARY KEY,
    username VARCHAR(150) NOT NULL,
    password VARCHAR(128) NOT NULL,
    role VARCHAR(20) NOT NULL,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE Account (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    parent_id INTEGER,
    role VARCHAR(20) NOT NULL,
    coins INTEGER NOT NULL DEFAULT 0,
    match_share DECIMAL(5, 2) NOT NULL DEFAULT 0,
    casino_share DECIMAL(5, 2) NOT NULL DEFAULT 0,
    commission_type VARCHAR(20) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES User (id),
    FOREIGN KEY (parent_id) REFERENCES Account (id)
);

CREATE TABLE CoinTransaction (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (account_id) REFERENCES Account (id)
);

CREATE TABLE AuditLog (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    action VARCHAR(255) NOT NULL,
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES User (id)
);
```

## APIs
The application provides the following APIs:

### User Management
- `POST /api/create-user/`: Create a new user.
- `GET /api/accounts/edit/<username>/`: Edit user account details.
- `GET /api/get-account-data/<username>/`: Retrieve account data.

### Financial Operations
- `POST /api/deposit-coins/`: Deposit coins into an account.
- `POST /api/withdraw-coins/`: Withdraw coins from an account.
- `GET /api/account-statement/`: Retrieve account statement.

### Partnership Deeds
- `GET /api/deed/<username>/`: Retrieve partnership deed for a user.

### Authentication
- `POST /login/`: User login.
- `POST /logout/`: User logout.

## Conclusion
BetProject is a comprehensive solution for managing user roles, permissions, and financial transactions in a hierarchical structure. Its robust design ensures scalability, security, and ease of use, making it an ideal choice for organizations looking to manage complex role-based systems.