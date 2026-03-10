import { useState, useCallback } from 'react';

/**
 * Custom hook for managing student data.
 *
 * Fetches the full student list from GET /api/students and provides
 * addStudent(formData) for creating new students via POST /api/students.
 *
 * @returns {{ students: Array, loading: boolean, error: string|null, addStudent: Function, refetch: Function }}
 */
export default function useStudents() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/students');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStudents(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const addStudent = useCallback(
    async (formData) => {
      setError(null);
      const res = await fetch('/api/students', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const created = await res.json();
      setStudents((prev) => [...prev, created]);
      return created;
    },
    []
  );

  return { students, loading, error, addStudent, refetch };
}
