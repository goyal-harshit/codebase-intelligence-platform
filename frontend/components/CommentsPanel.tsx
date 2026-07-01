"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { getComments, postComment, deleteComment, Comment } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { MessageSquare, Send, Trash2, User, LogIn } from "lucide-react";

interface CommentsPanelProps {
  targetType: string;
  targetId: string;
}

export default function CommentsPanel({ targetType, targetId }: CommentsPanelProps) {
  const { user } = useAuth();
  const { data: comments, error, mutate } = useSWR<Comment[]>(
    // Comments require a signed-in user; skip the fetch when logged out.
    user ? `comments-${targetType}-${targetId}` : null,
    () => getComments(targetType, targetId)
  );

  const [newComment, setNewComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handlePost = async () => {
    if (!newComment.trim()) return;
    setIsSubmitting(true);
    try {
      await postComment(targetType, targetId, newComment);
      setNewComment("");
      mutate();
    } catch (err) {
      console.error("Failed to post comment", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this comment?")) return;
    try {
      await deleteComment(id);
      mutate();
    } catch (err) {
      console.error("Failed to delete comment", err);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-700">
      <div className="p-4 border-b border-slate-700 flex items-center gap-2">
        <MessageSquare className="w-5 h-5 text-indigo-400" />
        <h3 className="text-lg font-semibold text-slate-100">Comments</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!user && (
          <div className="text-slate-400 text-sm flex flex-col items-start gap-2 p-3 bg-slate-800/50 rounded">
            <span className="flex items-center gap-2">
              <LogIn className="w-4 h-4" />
              Sign in to read and post comments.
            </span>
            <Link
              href="/login"
              className="text-indigo-400 hover:text-indigo-300 font-medium"
            >
              Go to sign in →
            </Link>
          </div>
        )}
        {user && error && (
          <div className="text-red-400 text-sm p-3 bg-red-900/20 rounded">
            Failed to load comments.
          </div>
        )}
        {user && !comments && !error && (
          <div className="text-slate-400 text-sm animate-pulse">Loading comments...</div>
        )}
        {comments?.length === 0 && (
          <div className="text-slate-400 text-sm italic">No comments yet. Be the first to comment!</div>
        )}
        {comments?.map((comment) => (
          <div key={comment.id} className="bg-slate-800 p-3 rounded-lg border border-slate-700 group">
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-indigo-500/20 flex items-center justify-center">
                  <User className="w-3 h-3 text-indigo-400" />
                </div>
                <span className="text-xs text-slate-400">
                  {new Date(comment.created_at).toLocaleString()}
                </span>
              </div>
              <button
                onClick={() => handleDelete(comment.id)}
                className="text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Delete comment"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            <div className="text-sm text-slate-200 whitespace-pre-wrap font-sans">
              {comment.body}
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-slate-700 bg-slate-800/50">
        <div className="flex gap-2">
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            disabled={!user}
            placeholder={
              user
                ? "Write a comment... (Markdown supported visually)"
                : "Sign in to post a comment"
            }
            className="flex-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none min-h-[80px] disabled:opacity-50 disabled:cursor-not-allowed"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                handlePost();
              }
            }}
          />
        </div>
        <div className="mt-2 flex justify-end items-center gap-2 text-xs text-slate-500">
          <span>Ctrl + Enter to post</span>
          <button
            onClick={handlePost}
            disabled={!user || isSubmitting || !newComment.trim()}
            className="flex items-center gap-1 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 text-white px-3 py-1.5 rounded-lg transition-colors font-medium text-sm"
          >
            {isSubmitting ? "Posting..." : "Post"}
            <Send className="w-4 h-4 ml-1" />
          </button>
        </div>
      </div>
    </div>
  );
}
