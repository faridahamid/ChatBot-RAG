# RAG ChatBot - Multi-Organization AI Assistant

## 🏗️ Project Structure

The project has been reorganized into a clean separation of frontend and backend:

```
ChatBot-RAG/
├── Frontend/                 # Frontend files
│   ├── css/                  # Stylesheets
│   │   └── main.css         # Main CSS file
│   ├── js/                   # JavaScript files
│   │   ├── common.js        # Common functions
│   │   ├── dashboard.js     # Dashboard functionality
│   │   ├── login.js         # Login functionality
│   │   └── welcome.js       # Welcome page functionality
│   └── pages/               # HTML pages
│       ├── welcome.html     # Welcome/landing page
│       ├── login.html       # Login page
│       ├── dashboard.html   # User dashboard
│       ├── admin_register.html # Admin registration
│       ├── admin_upload.html   # Admin file upload
│       └── admin_users.html    # Admin user management
├── Backend/                  # Backend files
│   ├── main.py              # Main FastAPI application
│   ├── admin_auth.py        # Authentication & user management
│   ├── database.py          # Database connection
│   ├── models.py            # Database models
│   ├── schemas.py           # Pydantic schemas
│   ├── ingestion.py         # Document processing
│   ├── llm.py               # LLM integration
│   └── requirements.txt     # Python dependencies
└── README.md                 # This file
```

## 🚀 Features

### ✨ **Core Functionality**

- **Multi-Organization Support**: Each organization has isolated data and AI assistant
- **Role-Based Access Control**: Admin and User roles with different permissions
- **AI-Powered Chat**: RAG technology for intelligent document-based responses
- **Document Management**: Upload and process various file types (PDF, DOCX, TXT, CSV)
- **Secure Authentication**: Password hashing and session management

### 🎯 **User Experience**

- **Modern UI**: Beautiful, responsive design with gradient backgrounds
- **Chat Interface**: Real-time AI chat for regular users
- **Admin Dashboard**: File upload and user management for administrators
- **Responsive Design**: Works perfectly on all device sizes

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8+
- PostgreSQL with pgvector extension
- Node.js (optional, for development)

### 1. Backend Setup

```bash
cd Backend

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
export GEMINI_API_KEY="your_gemini_api_key"
export DATABASE_URL="postgresql://user:password@localhost:5432/rag_chatbot"

# Create database and tables
python -c "from database import engine; from models import Base; Base.metadata.create_all(engine)"

# Create sample organizations
python setup_organizations.py

# Start the server
uvicorn main:app --reload
```

### 2. Frontend Setup

The frontend is served directly by the FastAPI backend, so no additional setup is required.

### 3. Access the System

- **Welcome Page**: http://localhost:8000/
- **Login**: http://localhost:8000/login
- **Admin Registration**: http://localhost:8000/admin-register
- **Dashboard**: http://localhost:8000/dashboard

## 🔧 Development

### Frontend Development

#### CSS Structure

- **`main.css`**: Comprehensive stylesheet with organized sections
  - Reset & Base Styles
  - Layout & Containers
  - Form Styles
  - Button Styles
  - Chat Interface
  - Responsive Design
  - Utility Classes
  - Animations

#### JavaScript Structure

- **`common.js`**: Shared functionality across all pages

  - Authentication & session management
  - Message display system
  - Form validation
  - API utilities
  - DOM utilities

- **`dashboard.js`**: Dashboard-specific functionality

  - User information loading
  - Chat interface management
  - Admin action handling

- **`login.js`**: Login page functionality

  - Form handling
  - Role selection
  - Authentication

- **`welcome.js`**: Welcome page functionality
  - Smooth scrolling
  - Animation effects
  - Navigation

### Backend Development

#### API Endpoints

- **Authentication**: `/admin/login`, `/admin/user/login`
- **User Management**: `/admin/create-user`, `/admin/organization-users/{org_id}`
- **Document Upload**: `/upload`
- **AI Chat**: `/ask`
- **Static Files**: `/css/{filename}`, `/js/{filename}`

#### Database Models

- **Organization**: Multi-tenant organization data
- **User**: User accounts with roles and organization association
- **Document**: Uploaded documents with metadata
- **DocumentChunk**: Processed document chunks for RAG
- **Chat**: Chat session tracking
- **ChatMessage**: Individual chat messages

## 🎨 Customization

### Styling

Modify `Frontend/css/main.css` to customize:

- Color schemes
- Layout dimensions
- Typography
- Animations
- Responsive breakpoints

### Functionality

Extend JavaScript files to add:

- New page features
- Additional API integrations
- Enhanced user interactions
- Custom animations

## 🧪 Testing

### Backend Testing

```bash
cd Backend

# Test admin functionality
python test_admin.py

# Test user management
python test_user_management.py

# Test chat functionality
python test_chat_functionality.py

# Test complete flow
python test_user_creation_login.py
```

### Frontend Testing

- Open browser developer tools
- Check console for JavaScript errors
- Verify CSS loading in Network tab
- Test responsive design at different screen sizes

## 🔒 Security Features

- **Password Hashing**: Bcrypt for secure password storage
- **Role Verification**: Server-side role validation
- **Organization Isolation**: Data separation between organizations
- **Session Management**: Secure user session handling
- **Input Validation**: Form and API input sanitization

## 📱 Responsive Design

The frontend is fully responsive with:

- Mobile-first approach
- Flexible grid layouts
- Adaptive typography
- Touch-friendly interactions
- Optimized for all screen sizes

## 🚀 Performance

### Frontend Optimization

- Minimal DOM manipulation
- Efficient event handling
- Optimized CSS with proper organization
- Lazy loading for chat messages

### Backend Optimization

- Async processing for file uploads
- Efficient database queries with pgvector
- Connection pooling
- Error handling and recovery

## 🐛 Troubleshooting

### Common Issues

#### Frontend Not Loading

- Check if backend server is running
- Verify file paths in main.py
- Check browser console for errors

#### CSS Not Applied

- Verify CSS file paths
- Check browser Network tab for 404 errors
- Clear browser cache

#### JavaScript Errors

- Check browser console
- Verify JavaScript file loading
- Check for syntax errors in JS files

### Debug Information

- Backend logs in terminal
- Browser developer tools
- Network request monitoring
- Database connection status

## 🔮 Future Enhancements

### Planned Features

- **Real-time Chat**: WebSocket support for live chat
- **File Sharing**: Direct file upload in chat
- **Voice Interface**: Speech-to-text integration
- **Advanced Analytics**: Usage statistics and insights
- **Multi-language Support**: Internationalization

### Technical Improvements

- **Progressive Web App**: PWA capabilities
- **Offline Support**: Service worker implementation
- **Performance Monitoring**: Analytics and metrics
- **Automated Testing**: Frontend and backend test suites

## 📚 Documentation

- **`README_ADMIN.md`**: Admin system documentation
- **`README_USER_MANAGEMENT.md`**: User management features
- **`README_ADMIN_UPLOAD.md`**: File upload system
- **`README_CHAT_FUNCTIONALITY.md`**: Chat interface documentation
- **`README_LOGIN_SYSTEM.md`**: Authentication system

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- Check the troubleshooting section
- Review the documentation files
- Open an issue on GitHub
- Contact the development team

---

**Happy coding! 🚀**
