import discord
from discord.ext import commands
from discord import app_commands
from Augmentations.Ai.Gen_role import gen_role
from Augmentations.Optimizations.Role_Creation import (
    show_roles, execute_roles, role_rep_to_dict, 
    delete_roles_efficiently, DeleteConfirmView, 
    create_chunk_roles
)

class RoleGen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="generate_roles", description="Generate roles using AI")
    async def generate_roles(self, interaction: discord.Interaction, roles_description: str):
        await interaction.response.defer()
        
        print(f"Generating roles based on description: {roles_description}")
        ai_response = await gen_role([{"role": "user", "content": f"Generate roles based on this description: {roles_description}"}])
        
        print("AI response received:")
        print(ai_response)  # Print the full AI response
        
        print("Converting to role dictionary...")
        roles_dict = role_rep_to_dict(ai_response)
        
        print("Showing roles to user...")
        embed, view = await show_roles(ai_response)
        await interaction.followup.send(embed=embed, view=view)
        
        view.roles = roles_dict
        view.interaction = interaction
        
        print("Waiting for user confirmation...")
        await view.wait()
        
        if view.value:
            print("User confirmed. Executing role creation...")
            await execute_roles(interaction.guild, roles_dict)
            await interaction.followup.send("Roles have been created successfully!")
        else:
            print("Role generation cancelled by user.")
            await interaction.followup.send("Role generation cancelled.")

    @app_commands.command(name="delete-all-roles", description="Delete all deletable roles in the server")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def delete_all_roles(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        if interaction.user.id != interaction.guild.owner_id:
            print("Non-owner attempted to delete all roles.")
            await interaction.followup.send("Only the server owner can use this command.")
            return

        confirm_view = DeleteConfirmView()
        await interaction.followup.send("Are you sure you want to delete all roles? This action cannot be undone.", view=confirm_view)
        
        await confirm_view.wait()
        
        if confirm_view.value:
            print("Starting deletion of all roles...")
            deleted_count, skipped_count = await delete_roles_efficiently(interaction.guild)
            await interaction.followup.send(f"Role deletion complete.\nDeleted roles: {deleted_count}\nSkipped roles: {skipped_count}")
        else:
            await interaction.followup.send("Role deletion cancelled.")
            
            
    @app_commands.command(name="generate_role_chunk", description="Generate a chunk of roles using AI and position them")
    @app_commands.describe(
        description="Description of the roles to generate",
        put_after="The role to place the new roles after (Optional)",
        put_before="The role to place the new roles before (Optional)"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def generate_role_chunk(
        self, 
        interaction: discord.Interaction, 
        description: str,
        put_after: discord.Role = None,
        put_before: discord.Role = None
    ):
        await interaction.response.defer()

        if put_after and put_before:
            await interaction.followup.send("Please specify only one of 'put_after' or 'put_before'.")
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.followup.send("I don't have permission to manage roles in this server.")
            return

        if (put_after and interaction.guild.me.top_role <= put_after) or (put_before and interaction.guild.me.top_role <= put_before):
            await interaction.followup.send("I can't create roles above or at the same level as my highest role.")
            return

        try:
            created_roles, count = await create_chunk_roles(interaction, description, put_after, put_before)
            if created_roles:
                position_info = ""
                if put_after:
                    position_info = f" The roles have been positioned after the '{put_after.name}' role."
                elif put_before:
                    position_info = f" The roles have been positioned before the '{put_before.name}' role."
                else:
                    position_info = " The roles have been positioned at the bottom of the role list."
                
                await interaction.followup.send(f"{count} roles have been created and positioned successfully!{position_info}")
            else:
                await interaction.followup.send("Role chunk generation cancelled.")
        except ValueError as e:
            await interaction.followup.send(str(e))
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to create or edit roles in this server.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"An error occurred while creating or positioning roles: {str(e)}")
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            await interaction.followup.send(f"An unexpected error occurred while generating role chunk. Please check the logs.")

async def setup(bot):
    await bot.add_cog(RoleGen(bot))