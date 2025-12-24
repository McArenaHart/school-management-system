def can_view_thread(user, thread) -> bool:
    if user.is_principal or user.is_school_admin:
        return True
    return user == thread.teacher_user or user == thread.parent_user
