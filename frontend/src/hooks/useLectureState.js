import { useEffect, useReducer, useCallback } from 'react';
import useWebSocket from './useWebSocket.js';

const MAX_TRANSCRIPT = 200;
const MAX_ALERTS = 20;

const initialState = {
  status: 'idle',
  transcript: [],
  boardElements: [],
  currentSlide: 1,
  students: {},
  geminiThinking: false,
  quotaUsed: 0,
  quotaRemaining: 250,
  alerts: [],
  speakingText: '',
  sessionId: null,
  topic: null,
};

/**
 * Reducer that applies WebSocket events to the lecture state.
 */
function reducer(state, action) {
  const { type, data } = action;

  switch (type) {
    case 'lecture_started':
      return {
        ...initialState,
        status: 'active',
        sessionId: data.session_id || null,
        topic: data.topic || null,
      };

    case 'lecture_paused':
      return { ...state, status: 'paused' };

    case 'lecture_resumed':
      return { ...state, status: 'active' };

    case 'lecture_ended':
      return { ...state, status: 'ended', speakingText: '' };

    case 'speaking_start':
      return { ...state, speakingText: data.text || '' };

    case 'speaking_end':
      return { ...state, speakingText: '' };

    case 'board_write':
    case 'board_draw':
    case 'board_highlight': {
      const position =
        data.position && typeof data.position === 'object'
          ? data.position
          : { x: 20, y: 20 + state.boardElements.length * 60 };
      const element = {
        id: data.id || data.element_id || `el-${Date.now()}-${Math.random()}`,
        type: data.element_type || data.type || 'text',
        content: data.content || '',
        position,
        style: data.style || {},
      };
      return { ...state, boardElements: [...state.boardElements, element] };
    }

    case 'board_clear':
      return { ...state, boardElements: [] };

    case 'slide_advanced':
      return { ...state, currentSlide: data.slide_number || state.currentSlide + 1 };

    case 'attendance_updated': {
      const updatedStudents = { ...state.students };
      if (data.students) {
        for (const s of data.students) {
          updatedStudents[s.id] = { ...updatedStudents[s.id], ...s };
        }
      }
      if (data.student_id) {
        updatedStudents[data.student_id] = {
          ...updatedStudents[data.student_id],
          ...data,
        };
      }
      return { ...state, students: updatedStudents };
    }

    case 'student_warned':
    case 'student_called': {
      const alert = {
        id: Date.now(),
        type,
        studentId: data.student_id,
        studentName: data.student_name || data.student_id,
        message: data.message || (type === 'student_warned' ? 'Warning issued' : 'Called on'),
        timestamp: Date.now(),
      };
      const alerts = [alert, ...state.alerts].slice(0, MAX_ALERTS);
      return { ...state, alerts };
    }

    case 'gemini_thinking':
      return { ...state, geminiThinking: data.thinking !== false };

    case 'quota_update':
      return {
        ...state,
        quotaUsed: data.used ?? state.quotaUsed,
        quotaRemaining: data.remaining ?? state.quotaRemaining,
      };

    case 'student_speech': {
      const speechText = data.text || data.transcript || '';
      const line = {
        id: Date.now(),
        speaker: 'STUDENT',
        text: speechText,
        studentId: data.student_id,
      };
      const transcript = [...state.transcript, line].slice(-MAX_TRANSCRIPT);
      return { ...state, transcript };
    }

    case 'tool_called': {
      if (data.tool_name === 'speak') {
        const line = {
          id: Date.now(),
          speaker: 'AI',
          text: data.args?.text || '',
        };
        const transcript = [...state.transcript, line].slice(-MAX_TRANSCRIPT);
        return { ...state, transcript };
      }
      return state;
    }

    case 'dismiss_alert': {
      return {
        ...state,
        alerts: state.alerts.filter((a) => a.id !== data.alertId),
      };
    }

    default:
      return state;
  }
}

/**
 * Custom hook that maintains full lecture state derived from WebSocket events.
 *
 * @returns {object} Lecture state + helper methods (dismissAlert, sendMessage)
 */
export default function useLectureState() {
  const { lastEvent, isConnected, sendMessage } = useWebSocket();
  const [state, dispatch] = useReducer(reducer, initialState);

  // Forward every incoming WebSocket event to the reducer
  useEffect(() => {
    if (!lastEvent) return;
    dispatch({ type: lastEvent.type, data: lastEvent.data || {} });
  }, [lastEvent]);

  const dismissAlert = useCallback((alertId) => {
    dispatch({ type: 'dismiss_alert', data: { alertId } });
  }, []);

  return {
    ...state,
    isConnected,
    sendMessage,
    dismissAlert,
  };
}
