import { z } from "zod";

export const authSchema = z.object({
  name: z.string().optional(),
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(6, "Password must be at least 6 characters."),
});

export const jobSchema = z.object({
  title: z.string().min(2, "Enter a job title."),
  location: z.string().min(2, "Enter a location."),
  workStyle: z.enum(["Hybrid", "Remote", "On-site"]),
  description: z.string().min(20, "Add a little more detail about this role."),
});

export type AuthInput = z.infer<typeof authSchema>;
export type JobInput = z.infer<typeof jobSchema>;
