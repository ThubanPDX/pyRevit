﻿using System;
using System.Windows.Forms;

namespace PyRevitLoader
{
    public partial class ScriptOutput : Form
    {
        public ScriptOutput()
        {
            InitializeComponent();
            txtStdOut.Text = "";            
        }

        private void ScriptOutput_Load(object sender, EventArgs e)
        {

        }
    }
}
